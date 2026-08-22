"""Idempotent event ingestion webhook (FR-01) + revenue risk scoring (FR-02)."""
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

    payment = Payment(
        id=payload.event_id,
        merchant_id=payload.merchant_id,
        customer_id=payload.customer_id,
        amount_paise=payload.amount_paise,
        currency="INR",
        payment_method=payload.payment_method,
        status="FAILED" if payload.event_type == "payment.failed" else "SUCCESS",
        failure_code=payload.failure_code,
        failure_reason=payload.failure_code,
    )
    db.add(payment)

    recovery_case_id = None
    if payload.event_type == "payment.failed":
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
            source_type="payment",
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
    return EventIngestResponse(
        event_id=payload.event_id,
        event_type=payload.event_type,
        ingested=True,
        duplicate=False,
        recovery_case_id=recovery_case_id,
    )
