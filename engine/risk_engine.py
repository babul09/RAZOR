"""Revenue risk engine (FR-02): deterministic risk scoring in integer terms.

Risk score = transaction_value_paise × failure_severity × recovery_probability
× customer_value_factor. Money stays integer paise (NFR-03); only the
multipliers are floats.
"""
from __future__ import annotations

# Failure severity by failure code (documented, deterministic).
FAILURE_SEVERITY: dict[str, float] = {
    "INSUFFICIENT_FUNDS": 1.0,
    "CARD_DECLINED": 1.1,
    "UPI_FAILURE": 0.9,
    "NETWORK_ERROR": 0.6,
    "AUTHENTICATION_FAILED": 0.8,
    "CHECKOUT_ABANDONED": 0.7,
    "FRAUD_SUSPECTED": 1.3,
}
DEFAULT_SEVERITY = 1.0


def build_severity(failure_code: str | None) -> float:
    return FAILURE_SEVERITY.get(failure_code or "", DEFAULT_SEVERITY)


def customer_value_factor(ltv_paise: int | None) -> float:
    ltv = ltv_paise or 0
    if ltv >= 10_000_000:
        return 1.5
    if ltv >= 5_000_000:
        return 1.3
    if ltv >= 1_000_000:
        return 1.1
    if ltv >= 200_000:
        return 1.0
    return 0.8


def compute_risk_score(
    transaction_value_paise: int,
    failure_severity: float,
    recovery_probability: float,
    customer_value_factor_value: float,
) -> int:
    """``transaction_value × severity × recovery_probability × value_factor`` (integer)."""
    if transaction_value_paise < 0:
        raise ValueError("transaction_value_paise must be non-negative")
    return int(
        transaction_value_paise
        * failure_severity
        * recovery_probability
        * customer_value_factor_value
    )
