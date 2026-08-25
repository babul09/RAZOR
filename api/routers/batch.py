"""Batch recovery execution endpoints (breadth + measured-real-batch).

Runs recovery cases across all four revenue-at-risk event types through the
real pipeline and records executed ``RecoveryAction`` / ``RecoveryOutcome``
rows, so dashboard money traces to executed outcomes. After a run the analytics
overview cache is invalidated so the headline reflects the measured batch.
"""
from __future__ import annotations

from fastapi import APIRouter

from api.errors import http_error
from api.routers.analytics import invalidate_overview_cache
from api.schemas import RecoveryBatchReport, RecoveryBatchRequest
from engine.policy_engine import MerchantPolicy, load_policy_yaml
from engine.recovery_batch import RecoveryBatchExecutor, SOURCE_TYPES
from ml.recovery_model import RecoveryModel

router = APIRouter(prefix="/api/recovery/batch", tags=["recovery-batch"])

MODEL_PATH = "ml/artifacts/recovery_model.joblib"
POLICY_PATH = "engine/policies/merchant_001.yaml"
DEFAULT_POLICY = MerchantPolicy(merchant_id="merchant_001")


@router.post("/run", response_model=RecoveryBatchReport)
def run_batch(body: RecoveryBatchRequest) -> RecoveryBatchReport:
    if body.limit < 1:
        raise http_error(400, "invalid_limit", "limit must be positive")
    invalid_types = [s for s in (body.source_types or []) if s not in SOURCE_TYPES]
    if invalid_types:
        raise http_error(
            400,
            "unsupported_source_type",
            f"unsupported source_type: {invalid_types[0]}; expected one of {sorted(SOURCE_TYPES)}",
        )

    model = RecoveryModel.load(MODEL_PATH)
    try:
        policy = load_policy_yaml(POLICY_PATH)
    except Exception:
        policy = DEFAULT_POLICY

    # Run inside the merchant's high-value window (policy wait 19-22) so cases
    # actually execute and measured recovery money is produced for the demo.
    executor = RecoveryBatchExecutor(model, policy, current_hour=20)
    result = executor.run(source_types=body.source_types, limit=body.limit)
    invalidate_overview_cache()
    return RecoveryBatchReport(
        processed_cases=result.processed_cases,
        executed=result.executed,
        recoveries=result.recoveries,
        at_risk_paise=result.at_risk_paise,
        recovered_paise=result.recovered_paise,
        cost_paise=result.cost_paise,
        incremental_paise=result.incremental_paise,
        per_source=[
            {
                "source_type": m.source_type,
                "processed": m.processed,
                "attempts": m.attempts,
                "recoveries": m.recoveries,
                "at_risk_paise": m.at_risk_paise,
                "recovered_paise": m.recovered_paise,
                "cost_paise": m.cost_paise,
            }
            for m in result.per_source
        ],
    )
