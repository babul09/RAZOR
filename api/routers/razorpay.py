"""Razorpay live-integration endpoints (Phase 9).

Exposes the side-by-side comparison (baseline vs RAZOR over real Razorpay test
payments) plus one-click recovery: RAZOR scores a real failed payment with the
ML model, chooses a strategy, and creates a Razorpay payment link (test mode).

If test keys aren't configured, the endpoints report ``configured=False`` and
return guidance instead of erroring, so the demo stays intact.
"""
from __future__ import annotations

import functools

from fastapi import APIRouter

from api.errors import http_error
from api.schemas import (
    RazorpayComparison,
    RazorpayHealth,
    RazorpayLink,
    RazorpayPayment,
    RazorpayRecoverRequest,
    RazorpayRecoverResponse,
    RazorpaySimSide,
)
from config import settings
from integrations import razorpay
from ml.training import TRAINING_STRATEGIES

router = APIRouter(prefix="/api/razorpay", tags=["razorpay"])

BASELINE_RECOVERY_RATE = 0.15  # naive, untargeted baseline recovery rate
RAZOR_CALIBRATION = 0.8        # conservative factor on model probabilities
RAZOR_TARGET_THRESHOLD = 0.30  # only intervene when model is confident


@functools.lru_cache(maxsize=1)
def _model():
    from ml.recovery_model import RecoveryModel
    return RecoveryModel.load("ml/artifacts/recovery_model.joblib")


def _masked_key() -> str | None:
    key = settings.razorpay_key_id
    if not key:
        return None
    return f"{key[:4]}…{key[-4:]}"


def _to_payment(p: dict) -> RazorpayPayment:
    return RazorpayPayment(
        id=p.get("id", ""),
        amount_paise=int(p.get("amount") or 0),
        currency=p.get("currency") or "INR",
        status=p.get("status") or "",
        method=(p.get("method") or "card").upper(),
        email=p.get("email"),
        contact=p.get("contact"),
        failure_code=razorpay.categorize_failure(p),
        failure_reason=p.get("error_description") or p.get("error_reason"),
        created_at=p.get("created_at"),
    )


def _best_strategy(features: dict) -> tuple[str, float]:
    model = _model()
    best = None
    best_prob = 0.0
    for strategy in TRAINING_STRATEGIES:
        prob = model.predict_proba(features, strategy)
        if prob > best_prob:
            best_prob, best = prob, strategy
    return best or "RETRY", best_prob


@router.get("/health", response_model=RazorpayHealth)
def health() -> RazorpayHealth:
    return RazorpayHealth(
        configured=razorpay.is_configured(),
        mode="test" if razorpay.is_configured() else "demo",
        key_id_masked=_masked_key(),
    )


@router.get("/payments", response_model=list[RazorpayPayment])
def list_payments(count: int = 50, status: str = "failed") -> list[RazorpayPayment]:
    if not razorpay.is_configured() and not razorpay.uses_mock():
        raise http_error(400, "razorpay_not_configured", "set RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET")
    try:
        items, _source = razorpay.fetch_payments(status=status, count=count)
    except razorpay.RazorpayError as exc:
        raise http_error(502, "razorpay_error", str(exc))
    return [_to_payment(p) for p in items]


@router.get("/links", response_model=list[RazorpayLink])
def list_links(count: int = 25) -> list[RazorpayLink]:
    if not razorpay.is_configured() and not razorpay.uses_mock():
        raise http_error(400, "razorpay_not_configured", "set RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET")
    try:
        items = razorpay.fetch_payment_links(count=count)
    except razorpay.RazorpayError as exc:
        raise http_error(502, "razorpay_error", str(exc))
    return [
        RazorpayLink(
            id=l.get("id", ""),
            amount_paise=int(l.get("amount") or 0),
            status=l.get("status") or "",
            short_url=l.get("short_url"),
            created_at=l.get("created_at"),
        )
        for l in items
    ]


@router.post("/recover", response_model=RazorpayRecoverResponse)
def recover(body: RazorpayRecoverRequest) -> RazorpayRecoverResponse:
    if not razorpay.is_configured() and not razorpay.uses_mock():
        raise http_error(400, "razorpay_not_configured", "set RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET")
    try:
        payment = razorpay.fetch_payment(body.payment_id)
    except razorpay.RazorpayError as exc:
        raise http_error(502, "razorpay_error", str(exc))

    features = razorpay.build_features(payment)
    strategy, prob = _best_strategy(features)
    amount = int(payment.get("amount") or 0)
    description = f"RAZOR recovery — {strategy.replace('_', ' ').title()}"

    try:
        link = razorpay.create_payment_link(
            amount,
            description=description,
            name=body.name or "",
            email=body.email or payment.get("email") or "",
            contact=body.contact or payment.get("contact") or "",
            notes={"payment_id": body.payment_id, "strategy": strategy, "source": "razor"},
        )
    except razorpay.RazorpayError as exc:
        raise http_error(502, "razorpay_error", f"payment link failed: {exc}")

    return RazorpayRecoverResponse(
        payment_id=body.payment_id,
        amount_paise=amount,
        strategy=strategy,
        recovery_probability=round(prob, 4),
        link_id=link.get("id"),
        short_url=link.get("short_url"),
        link_status=link.get("status"),
    )


@router.get("/comparison", response_model=RazorpayComparison)
def comparison(count: int = 50) -> RazorpayComparison:
    """Side-by-side: baseline vs RAZOR over Razorpay failed payments.

    Uses real test-API payments when keys are configured, otherwise realistic
    mock payments (clearly marked ``configured=False``).
    """
    if not razorpay.is_configured() and not razorpay.uses_mock():
        return RazorpayComparison(
            configured=False,
            source="sample",
            at_risk_paise=0,
            baseline=RazorpaySimSide(total_recovered_paise=0, recovery_rate=0.0, net_recovered_paise=0, interventions=0),
            razor=RazorpaySimSide(total_recovered_paise=0, recovery_rate=0.0, net_recovered_paise=0, interventions=0),
            incremental_paise=0,
        )
    try:
        items, source = razorpay.fetch_payments(status="failed", count=count)
    except razorpay.RazorpayError as exc:
        raise http_error(502, "razorpay_error", str(exc))

    at_risk = 0
    baseline_recovered = 0
    razor_recovered = 0
    razor_interventions = 0
    for p in items:
        amount = int(p.get("amount") or 0)
        at_risk += amount
        baseline_recovered += amount * BASELINE_RECOVERY_RATE
        _, prob = _best_strategy(razorpay.build_features(p))
        if prob >= RAZOR_TARGET_THRESHOLD:
            razor_interventions += 1
        razor_recovered += amount * prob * RAZOR_CALIBRATION

    baseline = RazorpaySimSide(
        total_recovered_paise=int(baseline_recovered),
        recovery_rate=baseline_recovered / at_risk if at_risk else 0.0,
        net_recovered_paise=int(baseline_recovered),
        interventions=len(items),
    )
    razor = RazorpaySimSide(
        total_recovered_paise=int(razor_recovered),
        recovery_rate=razor_recovered / at_risk if at_risk else 0.0,
        net_recovered_paise=int(razor_recovered),
        interventions=razor_interventions,
    )
    return RazorpayComparison(
        configured=razorpay.is_configured(),
        source=source,
        at_risk_paise=at_risk,
        baseline=baseline,
        razor=razor,
        incremental_paise=razor.net_recovered_paise - baseline.net_recovered_paise,
    )
