"""Simulator-backed action executor (FR-08) and outcome verifier (FR-10).

Executes a recovery action against the Phase 1 oracle and records the outcome
to ``recovery_outcomes``, updating the case to RECOVERED or FAILED. Fully
offline — no real payment APIs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from db.database import SessionLocal
from db.models import RecoveryCase, RecoveryCaseStatus, RecoveryOutcome
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
    """Records a recovery outcome and updates the case status."""

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
    ) -> RecoveryOutcome:
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
            session.commit()
            return outcome
        finally:
            session.close()
