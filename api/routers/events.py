"""Idempotent event ingestion webhook (FR-01) + revenue risk scoring (FR-02).

Supports all FR-01 event types. Creates recovery cases for revenue-at-risk
events: payment.failed, checkout.abandoned, subscription.failed, invoice.overdue.
Non-revenue events (payment.success, refund.created, dispute.created) are logged
but do not create cases.

Note: Other event types beyond REVENUE_RISK_EVENTS are intentionally unwired
from the recovery flow per design - they are accepted for logging/auditing but
do not trigger automated recovery actions.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.errors import http_error
from api.schemas import EventIngestRequest, EventIngestResponse
from db.database import get_db
from db.models import (
    Customer,
    CustomerRecoveryProfile,
    Payment,
    RecoveryCase,
    RecoveryCaseStatus,
)
from engine.risk_engine import (
    build_severity,
    compute_risk_score,
    customer_value_factor,
)
from agents.tasks import dispatch_diagnosis

router = APIRouter(prefix="/api/events", tags=["events"])

SUPPORTED_EVENT_TYPES = {
    "payment.failed",
    "payment.success",
    "checkout.abandoned",
    "invoice.overdue",
    "subscription.failed",
    "refund.created",
    "dispute.created",
}

# Event types that create revenue-at-risk recovery cases.
# These are wired to the full recovery flow (diagnosis → decision → execution).
REVENUE_RISK_EVENTS = {
    "payment.failed",
    "checkout.abandoned",
    "subscription.failed",
    "invoice.overdue",
}

DEFAULT_RECOVERY_PROBABILITY = 0.4


@router.post("/ingest", response_model=EventIngestResponse)
def ingest(payload: EventIngestRequest, db: Session = Depends(get_db)) -> EventIngestResponse:
    if payload.event_type not in SUPPORTED_EVENT_TYPES:
        raise http_error(400, "unsupported_event_type", f"unsupported event_type: {payload.event_type}")

    # Idempotency: a Payment keyed by event_id means this event was handled.
    if db.get(Payment, payload.event_id) is not None:
        return EventIngestResponse(
            event_id=payload.event_id,
            event_type=payload.event_type,
            ingested=False,
            duplicate=True,
        )

    customer = db.get(Customer, payload.customer_id)
    profile = (
        db.query(CustomerRecoveryProfile)
        .filter_by(customer_id=payload.customer_id)
        .first()
    )
    recovery_probability = (
        profile.overall_recovery_probability
        if profile and profile.overall_recovery_probability is not None
        else DEFAULT_RECOVERY_PROBABILITY
    )

    # Determine payment status based on event type.
    is_failed_event = payload.event_type in {"payment.failed", "checkout.abandoned", "subscription.failed"}
    payment_status = "FAILED" if is_failed_event else "SUCCESS"

    payment = Payment(
        id=payload.event_id,
        merchant_id=payload.merchant_id,
        customer_id=payload.customer_id,
        amount_paise=payload.amount_paise,
        currency="INR",
        payment_method=payload.payment_method,
        status=payment_status,
        failure_code=payload.failure_code,
        failure_reason=payload.failure_code,
    )
    db.add(payment)

    recovery_case_id = None
    # Create recovery case for revenue-at-risk events.
    if payload.event_type in REVENUE_RISK_EVENTS:
        severity = build_severity(payload.failure_code)
        value_factor = customer_value_factor(
            customer.lifetime_value_paise if customer else None
        )
        risk = compute_risk_score(
            payload.amount_paise,
            severity,
            float(recovery_probability),
            value_factor,
        )
        case = RecoveryCase(
            merchant_id=payload.merchant_id,
            customer_id=payload.customer_id,
            source_type=payload.event_type.split(".")[0],  # e.g., "payment", "checkout"
            source_id=payload.event_id,
            amount_at_risk_paise=payload.amount_paise,
            failure_code=payload.failure_code,
            failure_reason=payload.failure_code,
            status=RecoveryCaseStatus.NEW.value,
            priority=risk,
        )
        db.add(case)
        db.flush()
        recovery_case_id = case.id

    db.commit()
    if recovery_case_id is not None:
        # Trigger async Gemini diagnosis via Celery (inline fallback if broker down).
        dispatch_diagnosis(recovery_case_id)
    return EventIngestResponse(
        event_id=payload.event_id,
        event_type=payload.event_type,
        ingested=True,
        duplicate=False,
        recovery_case_id=recovery_case_id,
    )
