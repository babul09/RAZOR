"""Analytics endpoints with Redis caching (NFR-01) and integer-paise money (NFR-03)."""
from __future__ import annotations

import json

import redis
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.schemas import AnalyticsOverview, StrategyMetric
from config import settings
from db.database import get_db
from db.models import RecoveryAction, RecoveryCase, RecoveryCaseStatus, RecoveryOutcome

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

_cache = redis.Redis.from_url(settings.redis_url)
OVERVIEW_KEY = "razor:analytics:overview"
CACHE_TTL = 30  # seconds


def _cache_get(key: str):
    try:
        value = _cache.get(key)
        return json.loads(value) if value else None
    except Exception:
        return None


def _cache_set(key: str, data: dict) -> None:
    try:
        _cache.setex(key, CACHE_TTL, json.dumps(data))
    except Exception:
        pass


@router.get("/overview", response_model=AnalyticsOverview)
def overview(db: Session = Depends(get_db)) -> AnalyticsOverview:
    cached = _cache_get(OVERVIEW_KEY)
    if cached is not None:
        return AnalyticsOverview(**cached)

    at_risk = db.query(func.coalesce(func.sum(RecoveryCase.amount_at_risk_paise), 0)).scalar() or 0
    recovered = (
        db.query(func.coalesce(func.sum(RecoveryOutcome.revenue_recovered_paise), 0)).scalar() or 0
    )
    total_cases = db.query(RecoveryCase).count()
    recovered_cases = (
        db.query(RecoveryCase)
        .filter(RecoveryCase.status == RecoveryCaseStatus.RECOVERED.value)
        .count()
    )
    recovery_rate = recovered / at_risk if at_risk else 0.0
    data = {
        "revenue_at_risk_paise": int(at_risk),
        "recovered_paise": int(recovered),
        "recovery_rate": float(recovery_rate),
        "total_cases": int(total_cases),
        "recovered_cases": int(recovered_cases),
    }
    _cache_set(OVERVIEW_KEY, data)
    return AnalyticsOverview(**data)


@router.get("/strategies", response_model=list[StrategyMetric])
def strategies(db: Session = Depends(get_db)) -> list[StrategyMetric]:
    outcome_rows = (
        db.query(
            RecoveryOutcome.recovery_method,
            func.count(RecoveryOutcome.id),
            func.coalesce(func.sum(RecoveryOutcome.revenue_recovered_paise), 0),
            func.coalesce(func.sum(RecoveryOutcome.cost_of_recovery_paise), 0),
        )
        .group_by(RecoveryOutcome.recovery_method)
        .all()
    )
    action_rows = (
        db.query(RecoveryAction.strategy, func.count(RecoveryAction.id))
        .group_by(RecoveryAction.strategy)
        .all()
    )
    attempts = {name: int(count) for name, count in action_rows}
    metrics: dict[str, StrategyMetric] = {}
    for method, recoveries, recovered_paise, cost_paise in outcome_rows:
        metrics[method] = StrategyMetric(
            strategy=method,
            attempts=attempts.get(method, 0),
            recoveries=int(recoveries),
            recovered_paise=int(recovered_paise),
            cost_paise=int(cost_paise),
        )
    for name, count in action_rows:
        if name not in metrics:
            metrics[name] = StrategyMetric(
                strategy=name,
                attempts=int(count),
                recoveries=0,
                recovered_paise=0,
                cost_paise=0,
            )
    return sorted(metrics.values(), key=lambda m: m.recovered_paise, reverse=True)
