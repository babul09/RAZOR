"""A/B experiment results endpoint (reads DB; may be empty until Phase 6)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.schemas import ExperimentArmMetric
from db.database import get_db
from db.models import Experiment, ExperimentArm

router = APIRouter(prefix="/api/experiments", tags=["experiments"])


@router.get("", response_model=list[ExperimentArmMetric])
def experiments(db: Session = Depends(get_db)) -> list[ExperimentArmMetric]:
    rows = (
        db.query(Experiment, ExperimentArm)
        .join(ExperimentArm, ExperimentArm.experiment_id == Experiment.id)
        .all()
    )
    return [
        ExperimentArmMetric(
            experiment_id=experiment.id,
            experiment_name=experiment.name,
            arm_name=arm.arm_name,
            traffic_percent=arm.traffic_percent,
            strategy=arm.strategy,
            attempts=arm.attempts,
            recoveries=arm.recoveries,
            revenue_recovered_paise=arm.revenue_recovered_paise,
        )
        for experiment, arm in rows
    ]
