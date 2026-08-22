"""Feature engineering shared by simulation and future ML training."""
from __future__ import annotations

import pandas as pd

from simulation.generator import EventRecord

PAYMENT_METHOD_MAP = {"upi": 0, "card": 1, "netbanking": 2, "wallet": 3}
FAILURE_CODE_MAP = {
    "INSUFFICIENT_FUNDS": 0, "CARD_DECLINED": 1, "UPI_FAILURE": 2,
    "NETWORK_ERROR": 3, "AUTHENTICATION_FAILED": 4, "CHECKOUT_ABANDONED": 5,
    "FRAUD_SUSPECTED": 6,
}
SEGMENT_MAP = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}


def build_feature_vector(event: EventRecord) -> dict:
    return {
        "transaction_amount_paise": event.transaction_amount_paise,
        "payment_method_encoded": PAYMENT_METHOD_MAP[event.payment_method],
        "failure_code_encoded": FAILURE_CODE_MAP[event.failure_code],
        "customer_ltv_paise": event.customer_ltv_paise,
        "previous_successes": event.previous_successes,
        "previous_failures": event.previous_failures,
        "time_since_last_payment_days": event.days_since_last_payment,
        "historical_payment_hour": event.historical_payment_hour,
        "historical_payment_day": event.historical_payment_day,
        "retry_success_rate": event.retry_success_rate,
        "whatsapp_success_rate": event.whatsapp_success_rate,
        "upi_switch_success_rate": event.upi_switch_success_rate,
        "segment_encoded": SEGMENT_MAP[event.segment],
    }


def build_feature_dataframe(events: list[EventRecord]) -> pd.DataFrame:
    return pd.DataFrame([build_feature_vector(event) for event in events])