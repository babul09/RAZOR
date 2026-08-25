"""Batch recovery executor (breadth + measured-real-batch).

Wires ALL four revenue-at-risk source types — payment, checkout, subscription,
invoice — through the real pipeline: features -> decision (WAIT/STOP) -> policy
hard gate -> action execution -> outcome. Recovery money is recorded as executed
``RecoveryAction`` + ``RecoveryOutcome`` rows (FR-08 / FR-10) so the dashboard's
overview and incremental headline trace to executed outcomes, not the standalone
synthetic simulation.

All money arithmetic stays in integer paise (NFR-03). The LLM is never in the
money/execution path (NFR-05); policy remains a hard gate before any action
(NFR-07).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from db.database import SessionLocal
from db.models import (
    AgentDecision,
    Customer,
    CustomerRecoveryProfile,
    Payment,
    RecoveryAction,
    RecoveryCase,
    RecoveryCaseStatus,
    RecoveryOutcome,
)
from engine.decision_engine import DecisionEngine
from engine.outcome_verifier import ActionExecutor
from engine.policy_engine import MerchantPolicy, PolicyEngine
from engine.state_machine import RecoveryStateMachine, StateEvent
from ml.recovery_model import RecoveryModel

# Naive, untargeted baseline recovery rate used to measure incremental value.
BASELINE_RECOVERY_RATE = 0.15

# All revenue-at-risk source types wired through execution (breadth).
SOURCE_TYPES = ("payment", "checkout", "subscription", "invoice")

# Cases eligible to be picked up by a batch run.
_EXECUTABLE_STATUSES = (
    RecoveryCaseStatus.NEW,
    RecoveryCaseStatus.STRATEGY_SELECTED,
    RecoveryCaseStatus.FAILED,
)

# Strategies that take no immediate revenue action.
_NO_ACTION = {"WAIT", "STOP"}


@dataclass
class BatchSourceMetric:
    source_type: str
    processed: int = 0
    attempts: int = 0
    recoveries: int = 0
    at_risk_paise: int = 0
    recovered_paise: int = 0
    cost_paise: int = 0


@dataclass
class RecoveryBatchResult:
    processed_cases: int = 0
    executed: int = 0
    recoveries: int = 0
    at_risk_paise: int = 0
    recovered_paise: int = 0
    cost_paise: int = 0
    incremental_paise: int = 0
    per_source: list[BatchSourceMetric] = field(default_factory=list)


class _ManualDecision:
    """Minimal decision view for policy checks on operator-chosen actions."""

    def __init__(self, strategy: str):
        self.selected_strategy = strategy


class RecoveryBatchExecutor:
    """Runs a batch of recovery cases to executed outcomes, per event type."""

    def __init__(
        self,
        model: RecoveryModel,
        policy: MerchantPolicy,
        session_factory: Callable = SessionLocal,
        current_hour: int = 14,
        seed: int = 42,
    ):
        self.decision_engine = DecisionEngine(model, wait_window=policy.wait_window)
        self.policy_engine = PolicyEngine(policy)
        self.state_machine = RecoveryStateMachine()
        self.executor = ActionExecutor(seed=seed)
        self.session_factory = session_factory
        self.current_hour = current_hour
        self.discount_rate = policy.max_discount_rate

    # ------------------------------------------------------------------
    # Feature building (single source of truth shared by all event types)
    # ------------------------------------------------------------------

    def _features(
        self,
        case: RecoveryCase,
        payment: Payment | None,
        customer: Customer | None,
        profile: CustomerRecoveryProfile | None,
    ) -> dict[str, object]:
        amount = payment.amount_paise if payment else case.amount_at_risk_paise
        return {
            "transaction_amount_paise": amount,
            "payment_method": (
                (payment.payment_method if payment and payment.payment_method else "upi")
            ),
            "failure_code": (
                (payment.failure_code if payment and payment.failure_code else case.failure_code)
                or "INSUFFICIENT_FUNDS"
            ),
            "customer_ltv_paise": (customer.lifetime_value_paise if customer else 0),
            "previous_successes": (profile.retry_successes if profile else 0),
            "previous_failures": (profile.retry_attempts if profile else 0),
            "time_since_last_payment_days": 5.0,
            "historical_payment_hour": (
                customer.typical_payment_hour_start
                if customer and customer.typical_payment_hour_start is not None
                else 14
            ),
            "historical_payment_day": 2,
            "previous_strategy": "RETRY",
            "previous_strategy_success_rate": (
                profile.overall_recovery_probability if profile else 0.4
            ),
        }

    # ------------------------------------------------------------------
    # Per-case execution
    # ------------------------------------------------------------------

    def _execute_case(
        self,
        session,
        case: RecoveryCase,
        customer: Customer | None,
        profile: CustomerRecoveryProfile | None,
        strategy: str,
    ) -> RecoveryOutcome:
        """Execute one action, record the outcome + learning tuple, update status."""
        from db.models import AuditLog, RecoveryMemory
        from agents.diagnosis_agent import DiagnosisAgent

        segment = customer.customer_segment if customer and customer.customer_segment else "default"
        result = self.executor.attempt_recovery(segment, strategy, case.amount_at_risk_paise)

        action = RecoveryAction(
            case_id=case.id,
            strategy=strategy,
            cost_paise=result.cost_paise,
            status="COMPLETED",
            outcome="RECOVERED" if result.recovered else "FAILED",
            executed_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        session.add(action)

        outcome = RecoveryOutcome(
            case_id=case.id,
            action=action,
            revenue_recovered_paise=result.revenue_recovered_paise,
            cost_of_recovery_paise=result.cost_paise,
            net_revenue_recovered_paise=result.net_revenue_recovered_paise,
            recovery_method=strategy,
        )
        session.add(outcome)
        case.status = (
            RecoveryCaseStatus.RECOVERED.value
            if result.recovered
            else RecoveryCaseStatus.FAILED.value
        )

        session.add(
            RecoveryMemory(
                customer_id=case.customer_id,
                failure_type=case.failure_code,
                strategy=strategy,
                outcome="RECOVERED" if result.recovered else "FAILED",
                recovered=bool(result.recovered),
                amount_paise=result.revenue_recovered_paise,
            )
        )

        # Tell the story so the lab's step player + Gemini panel have content:
        # diagnosis (rule-based here, Gemini upgrades on demand), outcome, and a
        # plain-language explanation.
        if not session.query(AuditLog).filter_by(case_id=case.id, event_type="DIAGNOSIS").count():
            diagnosis = DiagnosisAgent(client=None).diagnose(case, customer=customer, profile=profile)
            session.add(
                AuditLog(
                    case_id=case.id,
                    event_type="DIAGNOSIS",
                    details_json=diagnosis.to_dict(),
                )
            )
        session.add(
            AuditLog(
                case_id=case.id,
                event_type="OUTCOME",
                details_json={
                    "strategy": strategy,
                    "recovered": bool(result.recovered),
                    "revenue_recovered_paise": result.revenue_recovered_paise,
                    "cost_paise": result.cost_paise,
                    "net_paise": result.net_revenue_recovered_paise,
                    "status": "RECOVERED" if result.recovered else "FAILED",
                },
            )
        )
        if not session.query(AuditLog).filter_by(case_id=case.id, event_type="EXPLANATION").count():
            diag_text = "Payment failed and required recovery."
            existing_diag = (
                session.query(AuditLog)
                .filter_by(case_id=case.id, event_type="DIAGNOSIS")
                .first()
            )
            if existing_diag and existing_diag.details_json:
                diag_text = existing_diag.details_json.get("diagnosis", diag_text)
            session.add(
                AuditLog(
                    case_id=case.id,
                    event_type="EXPLANATION",
                    details_json={
                        "explanation": (
                            f"Selected {strategy} for this case. Diagnosis: {diag_text}. "
                            f"Outcome: {'recovered' if result.recovered else 'not recovered'}."
                        )
                    },
                )
            )
        return outcome

    # ------------------------------------------------------------------
    # Batch run
    # ------------------------------------------------------------------

    def run(
        self,
        source_types: list[str] | None = None,
        limit: int = 100,
    ) -> RecoveryBatchResult:
        selected = [s for s in (source_types or list(SOURCE_TYPES)) if s in SOURCE_TYPES]
        if not selected:
            selected = list(SOURCE_TYPES)

        report = RecoveryBatchResult()
        report.per_source = [BatchSourceMetric(source_type=s) for s in selected]
        source_index = {m.source_type: m for m in report.per_source}

        # One shared session for the whole batch to avoid per-case connection
        # churn; the decision engine persists into the same session.
        with self.session_factory() as session:
            self.decision_engine.session = session
            ids = (
                session.query(RecoveryCase.id)
                .filter(
                    RecoveryCase.source_type.in_(selected),
                    RecoveryCase.status.in_([s.value for s in _EXECUTABLE_STATUSES]),
                )
                .order_by(RecoveryCase.priority.desc())
                .limit(max(limit, 1))
                .all()
            )
            case_ids = [row[0] for row in ids]

            for case_id in case_ids:
                self._process_case(case_id, report, source_index, session)

            report.incremental_paise = report.recovered_paise - int(
                report.at_risk_paise * BASELINE_RECOVERY_RATE
            )
        # Release the injected session so the engine falls back to its own.
        self.decision_engine.session = None
        return report

    def _process_case(self, case_id: str, report: RecoveryBatchResult, source_index, session) -> None:
        case = session.get(RecoveryCase, case_id)
        if case is None:
            return
        source = case.source_type or "payment"
        metric = source_index.get(source, BatchSourceMetric(source_type=source))
        report.processed_cases += 1
        metric.processed += 1

        payment = session.get(Payment, case.source_id) if case.source_id else None
        customer = session.get(Customer, case.customer_id) if case.customer_id else None
        profile = (
            session.query(CustomerRecoveryProfile)
            .filter_by(customer_id=case.customer_id)
            .first()
        )
        feats = self._features(case, payment, customer, profile)

        decision = self.decision_engine.decide(
            case,
            feats,
            current_hour=self.current_hour,
            discount_rate=self.discount_rate,
        )
        strategy = decision.selected_strategy

        # WAIT/STOP take no revenue action now.
        if strategy in _NO_ACTION:
            session.commit()
            session.expunge_all()
            return

        policy = self.policy_engine.check(
            decision, case.amount_at_risk_paise, discount_rate=self.discount_rate
        )

        if not policy.passed:
            self._audit_policy(session, case, policy)
            if strategy != "STOP":
                case.status = RecoveryCaseStatus.AWAITING_APPROVAL.value
            session.commit()
            session.expunge_all()
            return

        # Policy gate passed -> advance to executing, then execute.
        if case.status == RecoveryCaseStatus.STRATEGY_SELECTED.value:
            try:
                case.status = self.state_machine.next_status(
                    RecoveryCaseStatus.STRATEGY_SELECTED, StateEvent.POLICY_PASSED
                ).value  # POLICY_CHECK
                case.status = self.state_machine.next_status(
                    RecoveryCaseStatus.POLICY_CHECK, StateEvent.APPROVED
                ).value  # EXECUTING
            except ValueError:
                pass

        outcome = self._execute_case(session, case, customer, profile, strategy)
        # Capture values before commit expires + expunge_all detaches them.
        amount = case.amount_at_risk_paise
        recovered = outcome.revenue_recovered_paise
        cost = outcome.cost_of_recovery_paise
        session.commit()
        session.expunge_all()

        report.executed += 1
        metric.attempts += 1
        report.at_risk_paise += amount
        metric.at_risk_paise += amount
        report.recovered_paise += recovered
        metric.recovered_paise += recovered
        report.cost_paise += cost
        metric.cost_paise += cost
        if recovered > 0:
            report.recoveries += 1
            metric.recoveries += 1

    # ------------------------------------------------------------------
    # Operator-in-the-loop (manual action / approvals)
    # ------------------------------------------------------------------

    def execute_manual(
        self,
        case_id: str,
        strategy: str,
        discount_rate: float = 0.0,
    ) -> dict:
        """Run an operator-chosen action for a case: policy check, then execute.

        Policy stays a hard gate — a blocked action routes to human review
        instead of executing. Returns a plain dict for the API.
        """
        from db.models import AuditLog

        with self.session_factory() as session:
            self.decision_engine.session = session
            case = session.get(RecoveryCase, case_id)
            if case is None:
                return {"ok": False, "error": "case not found"}

            customer = session.get(Customer, case.customer_id) if case.customer_id else None
            profile = (
                session.query(CustomerRecoveryProfile)
                .filter_by(customer_id=case.customer_id)
                .first()
            )

            decision = _ManualDecision(strategy)
            policy = self.policy_engine.check(
                decision, case.amount_at_risk_paise, discount_rate=discount_rate
            )
            # Always record the operator's chosen action so it can be approved.
            session.add(
                AgentDecision(
                    case_id=case.id,
                    selected_strategy=strategy,
                    reasoning=f"Operator selected {strategy}",
                    policy_check_passed=policy.passed,
                )
            )
            if not policy.passed:
                session.add(
                    AuditLog(
                        case_id=case.id,
                        event_type="POLICY",
                        details_json={"status": policy.status, "reason": policy.reason},
                    )
                )
                case.status = RecoveryCaseStatus.AWAITING_APPROVAL.value
                session.commit()
                return {
                    "ok": True,
                    "executed": False,
                    "status": case.status,
                    "policy": policy.status,
                    "reason": policy.reason,
                }

            outcome = self._execute_case(session, case, customer, profile, strategy)
            result_status = case.status
            session.commit()
            return {
                "ok": True,
                "executed": True,
                "status": result_status,
                "policy": "PASS",
                "recovered": outcome.revenue_recovered_paise > 0,
                "recovered_paise": outcome.revenue_recovered_paise,
                "cost_paise": outcome.cost_of_recovery_paise,
            }

    def reject_case(self, case_id: str) -> dict:
        """Operator rejects a pending case — route it to STOPPED."""
        from db.models import AuditLog

        with self.session_factory() as session:
            case = session.get(RecoveryCase, case_id)
            if case is None:
                return {"ok": False, "error": "case not found"}
            session.add(
                AuditLog(
                    case_id=case.id,
                    event_type="POLICY",
                    details_json={"status": "REJECTED", "reason": "Rejected by operator"},
                )
            )
            case.status = RecoveryCaseStatus.STOPPED.value
            session.commit()
            return {"ok": True, "status": case.status}

    @staticmethod
    def _audit_policy(session, case: RecoveryCase, policy_result) -> None:
        from db.models import AuditLog

        session.add(
            AuditLog(
                case_id=case.id,
                event_type="POLICY",
                details_json={"status": policy_result.status, "reason": policy_result.reason},
            )
        )
