"""Strategy engine: expected-net-recovery selection with WAIT/STOP, DB logging.

Consumes ``RecoveryModel.predict_proba(features, strategy)`` for per-strategy
probabilities and ``STRATEGY_COSTS_PAISE`` for costs. Every decision writes one
``AgentDecision`` + one ``AuditLog`` and updates the ``RecoveryCase`` status
(AC-08). All money arithmetic stays in integer paise.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Mapping

import numpy as np

from db.database import SessionLocal
from db.models import AgentDecision, AuditLog, RecoveryCase, RecoveryCaseStatus
from ml.recovery_model import RecoveryModel
from simulation.razor_simulator import STRATEGY_COSTS_PAISE

from .state_machine import RecoveryStateMachine, StateEvent

# Strategies the Phase 2 model can score directly.
MODEL_STRATEGIES = [
    "RETRY",
    "PAYMENT_METHOD_SWITCH",
    "WHATSAPP_REMINDER",
    "EMAIL_REMINDER",
    "DISCOUNT_OFFER",
]


@dataclass
class EvaluatedStrategy:
    strategy: str
    probability: float
    cost_paise: int
    expected_net_paise: int


@dataclass
class Decision:
    case_id: str
    candidate_strategy: str
    selected_strategy: str
    expected_net_recovery_paise: int
    reasoning: str
    policy_check_passed: bool | None
    recommended_at: datetime | None
    status: str
    evaluated: list[EvaluatedStrategy] = field(default_factory=list)


class DecisionEngine:
    """Selects a recovery strategy by expected net recovery and logs it to PostgreSQL."""

    def __init__(
        self,
        model: RecoveryModel,
        state_machine: RecoveryStateMachine | None = None,
        wait_window: tuple[int | None, int | None] = (19, 22),
        session_factory: Callable = SessionLocal,
        strategy_weights: dict[str, float] | None = None,
    ):
        self.model = model
        self.state_machine = state_machine or RecoveryStateMachine()
        self.wait_window = wait_window
        self.session_factory = session_factory
        # FR-12: experiment-derived weights scale EV; default neutral 1.0.
        self.strategy_weights = dict(strategy_weights or {})

    def set_strategy_weights(self, weights: dict[str, float]) -> None:
        """Update per-strategy EV weights (experiment feedback)."""
        self.strategy_weights = {k: float(v) for k, v in weights.items()}

    def _weight(self, strategy: str) -> float:
        return self.strategy_weights.get(strategy, 1.0)

    # ------------------------------------------------------------------
    # Expected net recovery
    # ------------------------------------------------------------------

    def _candidates(self, discount_rate: float) -> list[str]:
        """Model-scored strategies; DISCOUNT_OFFER only when a discount is offered."""
        if discount_rate <= 0:
            return [s for s in MODEL_STRATEGIES if s != "DISCOUNT_OFFER"]
        return list(MODEL_STRATEGIES)

    def _probability(self, features: Mapping[str, Any], strategy: str) -> float:
        return self.model.predict_proba(features, strategy)

    def _cost(self, strategy: str, amount_paise: int, discount_rate: float) -> int:
        cost = STRATEGY_COSTS_PAISE[strategy]
        if strategy == "DISCOUNT_OFFER":
            # Dynamic discount cost, bounded later by policy max_discount_percent.
            cost = int(amount_paise * discount_rate)
        return int(cost) if cost is not None else 0

    def expected_net_recovery(
        self,
        features: Mapping[str, Any],
        strategy: str,
        amount_paise: int,
        discount_rate: float = 0.0,
    ) -> int:
        """``expected_net = P(recovery) * amount - cost`` in integer paise.

        Probability is scaled by the strategy weight (clamped to [0,1]).
        """
        probability = self._probability(features, strategy) * self._weight(strategy)
        probability = max(0.0, min(1.0, probability))
        cost = self._cost(strategy, amount_paise, discount_rate)
        return int(probability * amount_paise) - cost

    def _features_at_hour(self, features: Mapping[str, Any], hour: int) -> dict[str, Any]:
        copy = dict(features)
        copy["historical_payment_hour"] = hour
        return copy

    def evaluate_strategies(
        self,
        features: Mapping[str, Any],
        amount_paise: int,
        current_hour: int,
        discount_rate: float = 0.0,
    ) -> list[EvaluatedStrategy]:
        """Score all candidate strategies; ``current_hour`` reserved for timing."""
        results: list[EvaluatedStrategy] = []
        for strategy in self._candidates(discount_rate):
            probability = self._probability(features, strategy) * self._weight(strategy)
            probability = max(0.0, min(1.0, probability))
            cost = self._cost(strategy, amount_paise, discount_rate)
            net = int(probability * amount_paise) - cost
            results.append(EvaluatedStrategy(strategy, probability, cost, net))
        return results

    # ------------------------------------------------------------------
    # Decision
    # ------------------------------------------------------------------

    def _next_window_start(self, current_hour: int) -> datetime | None:
        start = self.wait_window[0]
        if start is None:
            return None
        now = datetime.utcnow()
        if now.hour < start:
            return now.replace(hour=start, minute=0, second=0, microsecond=0)
        return (now + timedelta(days=1)).replace(hour=start, minute=0, second=0, microsecond=0)

    def decide(
        self,
        case: RecoveryCase,
        features: Mapping[str, Any],
        current_hour: int,
        discount_rate: float = 0.0,
    ) -> Decision:
        """Evaluate strategies, apply WAIT/STOP, persist decision + audit + status."""
        amount = case.amount_at_risk_paise
        evaluated = self.evaluate_strategies(features, amount, current_hour, discount_rate)
        best = max(evaluated, key=lambda r: r.expected_net_paise)

        start, end = self.wait_window
        in_window = start is not None and end is not None and start <= current_hour < end

        selected = best.strategy
        expected_net = best.expected_net_paise
        reasoning = f"Selected {best.strategy}: expected net {best.expected_net_paise} paise"
        recommended_at: datetime | None = None

        # WAIT: outside the merchant's high-value window, a window-hour action
        # may beat the best action now (AC-04).
        if not in_window and start is not None:
            window_evs = [
                (
                    s,
                    self.expected_net_recovery(
                        self._features_at_hour(features, start), s, amount, discount_rate
                    ),
                )
                for s in self._candidates(discount_rate)
            ]
            best_window_strategy, best_window_net = max(window_evs, key=lambda x: x[1])
            if best_window_net > best.expected_net_paise:
                selected = "WAIT"
                expected_net = best_window_net
                recommended_at = self._next_window_start(current_hour)
                reasoning = (
                    f"WAIT until window start {start}:00; future EV "
                    f"{best_window_net} paise via {best_window_strategy} > now "
                    f"{best.expected_net_paise} paise"
                )

        # STOP: all real actions have negative expected net (AC: abandon).
        if selected != "WAIT" and best.expected_net_paise < 0:
            selected = "STOP"
            expected_net = best.expected_net_paise
            reasoning = (
                f"All strategies have negative expected net (max {best.expected_net_paise} paise); STOP"
            )

        decision = Decision(
            case_id=case.id,
            candidate_strategy=best.strategy,
            selected_strategy=selected,
            expected_net_recovery_paise=expected_net,
            reasoning=reasoning,
            policy_check_passed=None,
            recommended_at=recommended_at,
            status=RecoveryCaseStatus.STOPPED.value if selected == "STOP" else RecoveryCaseStatus.STRATEGY_SELECTED.value,
            evaluated=evaluated,
        )

        self._persist(case, decision, features, evaluated)
        return decision

    # ------------------------------------------------------------------
    # Persistence (direct PostgreSQL)
    # ------------------------------------------------------------------

    @staticmethod
    def _jsonable(value: Any) -> Any:
        """Coerce numpy/pandas scalar types to JSON-serializable Python types."""
        if isinstance(value, dict):
            return {str(k): DecisionEngine._jsonable(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [DecisionEngine._jsonable(v) for v in value]
        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.floating):
            return float(value)
        if isinstance(value, np.bool_):
            return bool(value)
        if isinstance(value, np.ndarray):
            return value.tolist()
        return value

    def _advance_status(
        self, status: RecoveryCaseStatus, decision: Decision
    ) -> RecoveryCaseStatus:
        if decision.selected_strategy == "STOP":
            return RecoveryCaseStatus.STOPPED
        # NEW -> DIAGNOSING -> PREDICTED -> STRATEGY_SELECTED for a fresh case.
        if status == RecoveryCaseStatus.NEW:
            status = self.state_machine.next_status(status, StateEvent.DIAGNOSED)
            status = self.state_machine.next_status(status, StateEvent.PREDICTED)
            status = self.state_machine.next_status(status, StateEvent.STRATEGY_SELECTED)
        return status

    def _persist(
        self,
        case: RecoveryCase,
        decision: Decision,
        features: Mapping[str, Any],
        evaluated: list[EvaluatedStrategy],
    ) -> None:
        evaluated_json = {r.strategy: r.expected_net_paise for r in evaluated}
        with self.session_factory() as session:
            persistent = session.merge(case)
            persistent.status = self._advance_status(persistent.status, decision)
            session.add(
                AgentDecision(
                    case_id=persistent.id,
                    input_json=self._jsonable(dict(features)),
                    strategies_evaluated_json=self._jsonable(evaluated_json),
                    selected_strategy=decision.selected_strategy,
                    reasoning=decision.reasoning,
                    policy_check_passed=decision.policy_check_passed,
                )
            )
            session.add(
                AuditLog(
                    case_id=persistent.id,
                    event_type="DECISION",
                    details_json={
                        "selected_strategy": decision.selected_strategy,
                        "candidate_strategy": decision.candidate_strategy,
                        "expected_net_paise": decision.expected_net_recovery_paise,
                        "reasoning": decision.reasoning,
                        "recommended_at": decision.recommended_at.isoformat() if decision.recommended_at else None,
                    },
                )
            )
            session.commit()
