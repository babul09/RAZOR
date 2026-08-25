"""Operator console endpoints (human-in-the-loop controls).

Payment limits, case approvals, and manual action selection for the demo.
Policy is stored in the ``Policy`` table so edits persist and take effect on
subsequent runs; a hard gate still blocks any action that violates a limit.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.errors import http_error
from api.routers.analytics import invalidate_overview_cache
from api.schemas import (
    ActionResult,
    ActionRequest,
    PolicyUpdateRequest,
    PolicyView,
)
from db.database import get_db
from db.models import AgentDecision, Policy
from engine.policy_engine import MerchantPolicy
from engine.recovery_batch import RecoveryBatchExecutor
from ml.recovery_model import RecoveryModel

router = APIRouter(prefix="/api", tags=["operator"])

MERCHANT_ID = "merchant_001"
MODEL_PATH = "ml/artifacts/recovery_model.joblib"

# Strategies an operator may pick for a pending case.
CHOOSABLE_STRATEGIES = [
    "RETRY",
    "PAYMENT_METHOD_SWITCH",
    "WHATSAPP_REMINDER",
    "EMAIL_REMINDER",
    "PAYMENT_LINK",
    "DISCOUNT_OFFER",
    "HUMAN_ESCALATION",
]


def _row_to_policy(row: Policy | None, merchant_id: str) -> MerchantPolicy:
    return MerchantPolicy(
        merchant_id=merchant_id,
        max_discount_percent=row.max_discount_percent if row else 10,
        max_automated_amount_paise=row.max_automated_amount_paise if row else 500_000,
        max_contacts_count=row.max_contacts_count if row else 3,
        max_contacts_window_days=row.max_contacts_window_days if row else 7,
        require_human_approval_above_paise=row.require_human_approval_above_paise if row else 500_000,
        allowed_channels=list(row.allowed_channels) if row and row.allowed_channels else ["whatsapp", "email"],
        stop_if_payment_succeeds=row.stop_if_payment_succeeds if row else True,
    )


def _view(row: Policy | None) -> PolicyView:
    return PolicyView(
        merchant_id=MERCHANT_ID,
        max_discount_percent=row.max_discount_percent if row else 10,
        max_automated_amount_paise=row.max_automated_amount_paise if row else 500_000,
        max_contacts_count=row.max_contacts_count if row else 3,
        max_contacts_window_days=row.max_contacts_window_days if row else 7,
        require_human_approval_above_paise=row.require_human_approval_above_paise if row else 500_000,
        allowed_channels=list(row.allowed_channels) if row and row.allowed_channels else ["whatsapp", "email"],
        stop_if_payment_succeeds=row.stop_if_payment_succeeds if row else True,
    )


def _executor(policy: MerchantPolicy) -> RecoveryBatchExecutor:
    return RecoveryBatchExecutor(RecoveryModel.load(MODEL_PATH), policy, current_hour=20)


# ---------------------------------------------------------------------------
# Payment limits
# ---------------------------------------------------------------------------


@router.get("/policy", response_model=PolicyView)
def get_policy(db: Session = Depends(get_db)) -> PolicyView:
    row = db.query(Policy).filter_by(merchant_id=MERCHANT_ID).first()
    return _view(row)


@router.put("/policy", response_model=PolicyView)
def update_policy(body: PolicyUpdateRequest, db: Session = Depends(get_db)) -> PolicyView:
    row = db.query(Policy).filter_by(merchant_id=MERCHANT_ID).first()
    if row is None:
        row = Policy(merchant_id=MERCHANT_ID)
        db.add(row)
    if body.max_discount_percent is not None:
        row.max_discount_percent = max(0, min(100, body.max_discount_percent))
    if body.max_automated_amount_paise is not None:
        row.max_automated_amount_paise = max(0, body.max_automated_amount_paise)
    if body.max_contacts_count is not None:
        row.max_contacts_count = max(0, body.max_contacts_count)
    if body.max_contacts_window_days is not None:
        row.max_contacts_window_days = max(0, body.max_contacts_window_days)
    if body.require_human_approval_above_paise is not None:
        row.require_human_approval_above_paise = max(0, body.require_human_approval_above_paise)
    if body.allowed_channels is not None:
        row.allowed_channels = body.allowed_channels
    if body.stop_if_payment_succeeds is not None:
        row.stop_if_payment_succeeds = body.stop_if_payment_succeeds
    db.commit()
    db.refresh(row)
    return _view(row)


# ---------------------------------------------------------------------------
# Approvals + manual action
# ---------------------------------------------------------------------------


def _exec_result(result: dict) -> ActionResult:
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error", "case not found"))
    return ActionResult(**result)


@router.post("/recovery/cases/{case_id}/action", response_model=ActionResult)
def take_action(case_id: str, body: ActionRequest, db: Session = Depends(get_db)) -> ActionResult:
    if body.strategy not in CHOOSABLE_STRATEGIES:
        raise http_error(400, "unsupported_strategy", f"strategy must be one of {CHOOSABLE_STRATEGIES}")
    policy = _row_to_policy(db.query(Policy).filter_by(merchant_id=MERCHANT_ID).first(), MERCHANT_ID)
    result = _executor(policy).execute_manual(
        case_id, body.strategy, discount_rate=body.discount_rate or 0.0
    )
    invalidate_overview_cache()
    return _exec_result(result)


@router.post("/recovery/cases/{case_id}/approve", response_model=ActionResult)
def approve_case(case_id: str, db: Session = Depends(get_db)) -> ActionResult:
    decision = (
        db.query(AgentDecision)
        .filter_by(case_id=case_id)
        .order_by(AgentDecision.created_at.desc())
        .first()
    )
    if decision is None or not decision.selected_strategy:
        raise http_error(400, "no_decision", "this case has no decision to approve")
    if decision.selected_strategy in ("WAIT", "STOP"):
        raise http_error(400, "not_approvable", f"cannot approve strategy {decision.selected_strategy}")
    policy = _row_to_policy(db.query(Policy).filter_by(merchant_id=MERCHANT_ID).first(), MERCHANT_ID)
    result = _executor(policy).execute_manual(case_id, decision.selected_strategy)
    invalidate_overview_cache()
    return _exec_result(result)


@router.post("/recovery/cases/{case_id}/reject", response_model=ActionResult)
def reject_case(case_id: str, db: Session = Depends(get_db)) -> ActionResult:
    policy = _row_to_policy(db.query(Policy).filter_by(merchant_id=MERCHANT_ID).first(), MERCHANT_ID)
    result = _executor(policy).reject_case(case_id)
    invalidate_overview_cache()
    return _exec_result(result)
