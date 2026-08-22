"""Razorpay test-API client for RAZOR (side-by-side comparison + live recovery).

Uses the official Razorpay REST API over httpx with HTTP Basic Auth
(``KEY_ID:KEY_SECRET``) against the sandbox base URL. See
https://razorpay.com/docs/api/ for payload shapes.

Relevant endpoints used here:
- ``GET /v1/payments`` — fetch payments (status can be filtered).
- ``GET /v1/payments/{id}`` — fetch a single payment.
- ``POST /v1/payment_links`` — create a payment link to collect a recovery.
- ``GET /v1/payment_links`` — fetch existing payment links.

The client never holds secrets in logs and returns normalized dicts so the API
layer can stay thin.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from config import settings

BASE_URL = settings.razorpay_base_url.rstrip("/")

# Mapping Razorpay payment error codes / reasons to RAZOR failure categories.
FAILURE_CATEGORY_BY_REASON: dict[str, str] = {
    "insufficient_funds": "INSUFFICIENT_FUNDS",
    "card_declined": "CARD_DECLINED",
    "incorrect_otp": "AUTHENTICATION_FAILED",
    "authentication_failed": "AUTHENTICATION_FAILED",
    "payment_failed": "CARD_DECLINED",
    "upi_failed": "UPI_FAILURE",
    "network_error": "NETWORK_ERROR",
}


class RazorpayError(Exception):
    """Raised when a Razorpay API call fails."""


def _basic_auth() -> tuple[str, str]:
    return (settings.razorpay_key_id, settings.razorpay_key_secret)


def is_configured() -> bool:
    return bool(settings.razorpay_key_id and settings.razorpay_key_secret)


def uses_mock() -> bool:
    """True when serving realistic mock data (no test keys + mock enabled)."""
    return (not is_configured()) and bool(settings.razorpay_mock)


def _request(method: str, path: str, *, params: dict | None = None, json: dict | None = None) -> dict:
    if not is_configured():
        raise RazorpayError("RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET not configured")
    url = f"{BASE_URL}{path}"
    try:
        resp = httpx.request(
            method, url, params=params, json=json, auth=_basic_auth(), timeout=15.0
        )
    except httpx.HTTPError as exc:  # network errors
        raise RazorpayError(f"Razorpay network error: {exc}") from exc
    if resp.status_code >= 400:
        detail = ""
        try:
            body = resp.json()
            detail = body.get("error", {}).get("description") or body.get("error", {}).get("code") or str(body)
        except Exception:
            detail = resp.text
        raise RazorpayError(f"Razorpay {resp.status_code}: {detail}")
    return resp.json()


def _payments_since(days: int) -> int:
    return int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())


def fetch_payments(status: str = "failed", count: int = 50, since_days: int = 30) -> list[dict]:
    """Fetch recent payments, filtered to ``status`` by default."""
    if uses_mock():
        return _mock_payments(status=status, count=count)
    count = max(1, min(count, 100))
    params = {
        "count": count,
        "from": _payments_since(since_days),
        "to": int(datetime.now(timezone.utc).timestamp()),
    }
    data = _request("GET", "/payments", params=params)
    items = data.get("items", [])
    if status:
        items = [p for p in items if p.get("status") == status]
    return items


def fetch_payment(payment_id: str) -> dict:
    if uses_mock():
        payments = _mock_payments(status="", count=200)
        for p in payments:
            if p.get("id") == payment_id:
                return p
        raise RazorpayError(f"mock payment not found: {payment_id}")
    return _request("GET", f"/payments/{payment_id}")


def fetch_payment_links(count: int = 25) -> list[dict]:
    if uses_mock():
        return _mock_links(count)
    data = _request("GET", "/payment_links", params={"count": max(1, min(count, 100))})
    return data.get("items", [])


def create_payment_link(
    amount_paise: int,
    *,
    description: str,
    name: str = "",
    email: str = "",
    contact: str = "",
    notes: dict | None = None,
    reminder_enable: bool = True,
) -> dict:
    """Create a standard payment link (the RAZOR recovery action) in test mode."""
    if uses_mock():
        return _mock_link(amount_paise, description=description, notes=notes or {})
    customer: dict = {}
    if name:
        customer["name"] = name
    if email:
        customer["email"] = email
    if contact:
        customer["contact"] = contact
    payload: dict = {
        "amount": int(amount_paise),
        "currency": "INR",
        "description": description,
        "accept_partial": False,
        "reminder_enable": reminder_enable,
        "notes": notes or {},
    }
    if customer:
        payload["customer"] = customer
    return _request("POST", "/payment_links", json=payload)


def categorize_failure(payment: dict) -> str:
    """Map a Razorpay payment's error fields to a RAZOR failure category."""
    reason = (payment.get("error_reason") or "").lower()
    code = (payment.get("error_code") or "").lower()
    for key in (reason, code):
        for frag, category in FAILURE_CATEGORY_BY_REASON.items():
            if frag in key:
                return category
    return "CARD_DECLINED"


def method_name(payment: dict) -> str:
    """Map a Razorpay payment method to a model-friendly token."""
    return (payment.get("method") or "card").upper()


def build_features(payment: dict) -> dict:
    """Build the ML feature vector from a Razorpay payment.

    Unknown historical fields fall back to conservative defaults so the model
    still scores real payments without leaking hidden segments.
    """
    return {
        "transaction_amount_paise": int(payment.get("amount") or 0),
        "payment_method": method_name(payment),
        "failure_code": categorize_failure(payment),
        "customer_ltv_paise": int((payment.get("notes") or {}).get("ltv_paise", 1000000)),
        "previous_successes": int((payment.get("notes") or {}).get("previous_successes", 3)),
        "previous_failures": int((payment.get("notes") or {}).get("previous_failures", 1)),
        "time_since_last_payment_days": 1.0,
        "historical_payment_hour": 12,
        "historical_payment_day": 3,
        "previous_strategy": "RETRY",
        "previous_strategy_success_rate": 0.4,
    }


# ---------------------------------------------------------------------------
# Mock mode — serves realistic Razorpay-shaped payloads when test keys are
# absent (demo mode). Mirrors the sandbox response shape exactly.
# ---------------------------------------------------------------------------

_MOCK_METHODS = ["card", "netbanking", "upi", "wallet", "emi"]
_MOCK_REASONS = [
    ("incorrect_otp", "Payment processing failed because of incorrect OTP", "AUTHENTICATION_FAILED"),
    ("card_declined", "Your card was declined by the bank", "CARD_DECLINED"),
    ("insufficient_funds", "The account has insufficient funds", "INSUFFICIENT_FUNDS"),
    ("network_error", "A network error occurred while processing", "NETWORK_ERROR"),
    ("payment_failed", "The payment failed, please try again", "CARD_DECLINED"),
]


def _mock_payments(status: str = "failed", count: int = 50) -> list[dict]:
    from simulation.generator import SyntheticDataGenerator

    count = max(1, min(count, 100))
    dataset = SyntheticDataGenerator(seed=7).generate(count * 2)
    events = dataset.events[:count]
    now = int(datetime.now(timezone.utc).timestamp())
    items: list[dict] = []
    for i, event in enumerate(events):
        reason, desc, _ = _MOCK_REASONS[i % len(_MOCK_REASONS)]
        items.append({
            "id": f"pay_{i:010d}",
            "entity": "payment",
            "amount": event.transaction_amount_paise,
            "currency": "INR",
            "status": status or ("failed" if i % 3 else "captured"),
            "method": _MOCK_METHODS[i % len(_MOCK_METHODS)],
            "order_id": None,
            "captured": False,
            "email": f"customer{i}@example.com",
            "contact": f"+919900000{i % 100:02d}",
            "error_code": "BAD_REQUEST_ERROR",
            "error_description": desc,
            "error_reason": reason,
            "notes": {
                "ltv_paise": event.customer_ltv_paise,
                "previous_successes": event.previous_successes,
                "previous_failures": event.previous_failures,
                "segment": event.segment,
            },
            "created_at": now - (i * 3600),
        })
    return items


def _mock_link(amount_paise: int, *, description: str, notes: dict) -> dict:
    return {
        "id": "plink_mock00000000",
        "entity": "payment_link",
        "amount": int(amount_paise),
        "currency": "INR",
        "status": "created",
        "short_url": "https://rzp.io/l/razor-demo",
        "description": description,
        "notes": notes,
        "created_at": int(datetime.now(timezone.utc).timestamp()),
    }


def _mock_links(count: int = 25) -> list[dict]:
    return [_mock_link(100000 + i * 50000, description=f"RAZOR recovery {i}", notes={}) for i in range(min(count, 10))]
