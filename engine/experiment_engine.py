"""A/B experiment engine (FR-12): create, allocate, track, and weight strategies."""
from __future__ import annotations

import hashlib
from typing import Any, Iterable

from sqlalchemy.orm import Session

from db.models import Experiment, ExperimentArm


class ExperimentEngine:
    """Defines experiments, allocates traffic, tracks arm metrics, and computes weights."""

    def create_experiment(
        self,
        session: Session,
        name: str,
        arms: Iterable[dict[str, Any]],
        merchant_id: str,
    ) -> Experiment:
        """Persist an Experiment + arms; validates traffic_percent sums to 100."""
        arm_list = list(arms)
        total = sum(int(a.get("traffic_percent", 0)) for a in arm_list)
        if total != 100:
            raise ValueError(f"traffic_percent must sum to 100, got {total}")
        experiment = Experiment(name=name, status="ACTIVE", merchant_id=merchant_id)
        session.add(experiment)
        session.flush()
        for a in arm_list:
            session.add(
                ExperimentArm(
                    experiment_id=experiment.id,
                    arm_name=str(a["arm_name"]),
                    traffic_percent=int(a["traffic_percent"]),
                    strategy=a.get("strategy"),
                )
            )
        session.commit()
        return experiment

    @staticmethod
    def allocate(
        arms: Iterable[dict[str, Any]],
        key: str,
        seed: int = 42,
    ) -> str | None:
        """Deterministically select an arm's strategy weighted by traffic_percent."""
        arm_list = list(arms)
        if not arm_list:
            return None
        total = sum(int(a.get("traffic_percent", 0)) for a in arm_list) or 1
        digest = int(hashlib.sha256(f"{key}:{seed}".encode("utf-8")).hexdigest()[:8], 16)
        target = (digest % 1000) / 1000.0 * total
        cumulative = 0
        for arm in arm_list:
            cumulative += int(arm.get("traffic_percent", 0))
            if target <= cumulative:
                return arm.get("strategy")
        return arm_list[-1].get("strategy")

    def record_arm_metric(
        self,
        session: Session,
        arm_id: str,
        recovered: bool,
        revenue_paise: int,
    ) -> ExperimentArm | None:
        """Increment an arm's attempts / recoveries / recovered revenue."""
        arm = session.get(ExperimentArm, arm_id)
        if arm is None:
            return None
        arm.attempts = (arm.attempts or 0) + 1
        if recovered:
            arm.recoveries = (arm.recoveries or 0) + 1
            arm.revenue_recovered_paise = (arm.revenue_recovered_paise or 0) + int(revenue_paise)
        session.commit()
        return arm

    def compute_strategy_weights(
        self,
        session: Session,
        experiments: Iterable[Experiment] | None = None,
    ) -> dict[str, float]:
        """Return normalized per-strategy weights from per-arm recovery rates.

        Higher recovery rate -> higher weight; best rate normalizes to 1.0.
        Strategies without data are absent (DecisionEngine defaults them to 1.0).
        """
        arms = session.query(ExperimentArm).all() if experiments is None else [
            arm for e in experiments for arm in e.arms
        ]
        rates: dict[str, float] = {}
        for arm in arms:
            if not arm.strategy or not arm.attempts:
                continue
            rates[arm.strategy] = arm.recoveries / arm.attempts
        if not rates:
            return {}
        best = max(rates.values()) or 1.0
        return {strategy: rate / best for strategy, rate in rates.items()}

    @staticmethod
    def apply_weights(engine: Any, weights: dict[str, float]) -> None:
        """Feed computed weights into a DecisionEngine."""
        engine.set_strategy_weights(weights)
