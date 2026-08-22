"""A/B experiment endpoints: create, list, and strategy weights."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.errors import http_error
from api.schemas import (
    ExperimentArmMetric,
    ExperimentCreateRequest,
    ExperimentCreateResponse,
)
from db.database import get_db
from db.models import Experiment, ExperimentArm
from engine.experiment_engine import ExperimentEngine

router = APIRouter(prefix="/api/experiments", tags=["experiments"])

_engine = ExperimentEngine()


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
            recovery_rate=(arm.recoveries / arm.attempts) if arm.attempts else None,
        )
        for experiment, arm in rows
    ]


@router.post("", response_model=ExperimentCreateResponse)
def create_experiment(
    body: ExperimentCreateRequest, db: Session = Depends(get_db)
) -> ExperimentCreateResponse:
    try:
        experiment = _engine.create_experiment(
            db,
            body.name,
            [a.model_dump() for a in body.arms],
            body.merchant_id,
        )
    except ValueError as exc:
        raise http_error(400, "invalid_experiment", str(exc)) from exc
    arms = [
        ExperimentArmMetric(
            experiment_id=experiment.id,
            experiment_name=experiment.name,
            arm_name=a.arm_name,
            traffic_percent=a.traffic_percent,
            strategy=a.strategy,
            attempts=a.attempts or 0,
            recoveries=a.recoveries or 0,
            revenue_recovered_paise=a.revenue_recovered_paise or 0,
        )
        for a in experiment.arms
    ]
    return ExperimentCreateResponse(
        id=experiment.id,
        name=experiment.name,
        status=experiment.status,
        arms=arms,
    )


@router.get("/weights", response_model=dict[str, float])
def strategy_weights(db: Session = Depends(get_db)) -> dict[str, float]:
    return _engine.compute_strategy_weights(db)
