"""Simulator-backed action executor (FR-08) and outcome verifier (FR-10).

Executes a recovery action against the Phase 1 oracle and records the outcome
to ``recovery_outcomes``, updating the case to RECOVERED or FAILED. Fully
offline — no real payment APIs.

Recovery money traces to executed outcomes via:
1. RecoveryOutcome recorded with actual revenue/cost
2. RecoveryMemory entry for learning loop (FR-11)
3. ExperimentArm metric update if part of an experiment (FR-12)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from db.database import SessionLocal
from db.models import (
    Customer,
    RecoveryCase,
    RecoveryCaseStatus,
    RecoveryMemory,
    RecoveryOutcome,
)
from engine.recovery_memory import record_outcome as record_recovery_memory
from simulation.razor_simulator import RECOVERY_PROBS, STRATEGY_COSTS_PAISE


@dataclass
class ExecutionResult:
    recovered: bool
    revenue_recovered_paise: int
    cost_paise: int
    net_revenue_recovered_paise: int
    recovery_method: str


class ActionExecutor:
    """Deterministic simulator-backed recovery attempt (no real APIs)."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    def attempt_recovery(
        self, segment: str, strategy: str, amount_paise: int
    ) -> ExecutionResult:
        probability = RECOVERY_PROBS.get(
            (segment, strategy, None),
            RECOVERY_PROBS[("default", None, None)],
        )
        recovered = bool(self.rng.random() < probability)
        cost = int(STRATEGY_COSTS_PAISE.get(strategy) or 0)
        revenue = amount_paise if recovered else 0
        return ExecutionResult(
            recovered=recovered,
            revenue_recovered_paise=revenue,
            cost_paise=cost,
            net_revenue_recovered_paise=revenue - cost,
            recovery_method=strategy,
        )


class OutcomeVerifier:
    """Records a recovery outcome and updates the case status.

    Traces recovery money to executed outcomes:
    - Records RecoveryOutcome with actual revenue/cost/net
    - Records RecoveryMemory for customer learning loop
    - Updates ExperimentArm metrics if case is part of an experiment
    """

    def __init__(
        self,
        executor: ActionExecutor | None = None,
        session_factory: Callable = SessionLocal,
    ):
        self.executor = executor or ActionExecutor()
        self.session_factory = session_factory

    def verify(
        self,
        case: RecoveryCase,
        segment: str,
        strategy: str,
        amount_paise: int,
        experiment_arm_id: str | None = None,
    ) -> RecoveryOutcome:
        """Execute recovery action and record outcome with full tracing.

        Args:
            case: The recovery case being verified
            segment: Customer segment (A/B/C/D/E)
            strategy: The recovery strategy executed
            amount_paise: Amount at risk/recovered
            experiment_arm_id: Optional experiment arm ID if part of A/B test

        Returns:
            RecoveryOutcome with actual executed results
        """
        result = self.executor.attempt_recovery(segment, strategy, amount_paise)
        session = self.session_factory()
        session.expire_on_commit = False
        try:
            persistent = session.merge(case)
            outcome = RecoveryOutcome(
                case_id=persistent.id,
                revenue_recovered_paise=result.revenue_recovered_paise,
                cost_of_recovery_paise=result.cost_paise,
                net_revenue_recovered_paise=result.net_revenue_recovered_paise,
                recovery_method=result.recovery_method,
            )
            session.add(outcome)
            persistent.status = (
                RecoveryCaseStatus.RECOVERED.value
                if result.recovered
                else RecoveryCaseStatus.FAILED.value
            )

            # FR-11: Record to recovery memory for learning loop
            customer = session.get(Customer, case.customer_id) if case.customer_id else None
            failure_type = case.failure_code
            outcome_str = "RECOVERED" if result.recovered else "FAILED"
            memory = record_recovery_memory(
                session=session,
                customer_id=case.customer_id,
                failure_type=failure_type,
                strategy=strategy,
                outcome=outcome_str,
                recovered=result.recovered,
                amount_paise=result.revenue_recovered_paise,
            )

            # FR-12: Update experiment arm metrics if applicable
            if experiment_arm_id is not None:
                from db.models import ExperimentArm
                arm = session.get(ExperimentArm, experiment_arm_id)
                if arm is not None:
                    arm.attempts = (arm.attempts or 0) + 1
                    if result.recovered:
                        arm.recoveries = (arm.recoveries or 0) + 1
                        arm.revenue_recovered_paise = (
                            (arm.revenue_recovered_paise or 0) + result.revenue_recovered_paise
                        )

            session.commit()
            return outcome
        finally:
            session.close()
