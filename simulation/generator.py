"""Deterministic synthetic payment-failure data for the RAZOR simulation."""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from faker import Faker


@dataclass
class EventRecord:
    event_id: str
    customer_id: str
    merchant_id: str
    segment: str
    transaction_amount_paise: int
    payment_method: str
    failure_code: str
    failure_category: str
    customer_ltv_paise: int
    previous_successes: int
    previous_failures: int
    subscription_age_days: int
    days_since_last_payment: float
    historical_payment_hour: int
    historical_payment_day: int
    timestamp: datetime
    retry_success_rate: float
    whatsapp_success_rate: float
    email_success_rate: float
    upi_switch_success_rate: float


@dataclass
class GeneratedDataset:
    events: list[EventRecord]
    customers: list[dict]
    profiles: list[dict]


class SyntheticDataGenerator:
    SEGMENTS = (("A", 0.25), ("B", 0.20), ("C", 0.20), ("D", 0.15), ("E", 0.20))
    FAILURE_CATEGORIES = {
        "INSUFFICIENT_FUNDS": "insufficient_funds",
        "CARD_DECLINED": "card_declined",
        "UPI_FAILURE": "upi_failure",
        "NETWORK_ERROR": "network_error",
        "AUTHENTICATION_FAILED": "authentication_failed",
        "CHECKOUT_ABANDONED": "checkout_abandoned",
        "FRAUD_SUSPECTED": "fraud_suspected",
    }

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.fake = Faker(locale="en_IN")
        self.fake.seed_instance(seed)

    def generate(self, n_events: int = 20_000) -> GeneratedDataset:
        if n_events < 1:
            raise ValueError("n_events must be positive")
        merchant_id = "merchant_001"
        events: list[EventRecord] = []
        customers: list[dict] = []
        profiles: list[dict] = []
        segment_counts = self._segment_counts(n_events)
        event_number = 0
        for segment, count in segment_counts.items():
            for _ in range(count):
                customer_id = str(uuid.UUID(int=self._next_uuid_int()))
                event = self._make_event(event_number, customer_id, merchant_id, segment)
                events.append(event)
                customers.append({
                    "id": customer_id,
                    "merchant_id": merchant_id,
                    "name": self.fake.name(),
                    "email": self.fake.email(),
                    "phone": self.fake.phone_number()[:20],
                    "lifetime_value_paise": event.customer_ltv_paise,
                    "preferred_payment_method": event.payment_method,
                    "typical_payment_hour_start": max(0, event.historical_payment_hour - 1),
                    "typical_payment_hour_end": min(23, event.historical_payment_hour + 1),
                    "customer_segment": segment,
                })
                profiles.append({
                    "customer_id": customer_id,
                    "merchant_id": merchant_id,
                    "overall_recovery_probability": event.retry_success_rate,
                    "retry_attempts": event.previous_failures,
                    "retry_successes": event.previous_successes,
                })
                event_number += 1
        dataset = GeneratedDataset(events=events, customers=customers, profiles=profiles)
        self._save(dataset, n_events)
        return dataset

    def _next_uuid_int(self) -> int:
        high = int(self.rng.integers(0, 2**64, dtype=np.uint64))
        low = int(self.rng.integers(0, 2**64, dtype=np.uint64))
        return (high << 64) | low

    def _segment_counts(self, n_events: int) -> dict[str, int]:
        raw = {segment: int(n_events * fraction) for segment, fraction in self.SEGMENTS}
        remainder = n_events - sum(raw.values())
        for segment, _ in self.SEGMENTS[:remainder]:
            raw[segment] += 1
        return raw

    def _make_event(self, index: int, customer_id: str, merchant_id: str, segment: str) -> EventRecord:
        ranges = {
            "A": ((50_000, 1_500_000), (2_000_000, 8_000_000), ("INSUFFICIENT_FUNDS", "CARD_DECLINED"), (0.8, 0.2)),
            "B": ((100_000, 2_000_000), (1_500_000, 6_000_000), ("UPI_FAILURE", "NETWORK_ERROR"), (0.7, 0.3)),
            "C": ((20_000, 800_000), (500_000, 3_000_000), ("AUTHENTICATION_FAILED", "CHECKOUT_ABANDONED"), (0.5, 0.5)),
            "D": ((500_000, 5_000_000), (10_000_000, 25_000_000), ("CARD_DECLINED", "FRAUD_SUSPECTED", "AUTHENTICATION_FAILED"), (0.4, 0.3, 0.3)),
            "E": ((5_000, 50_000), (0, 300_000), ("INSUFFICIENT_FUNDS", "CARD_DECLINED", "UPI_FAILURE"), (0.5, 0.3, 0.2)),
        }
        amount_range, ltv_range, failure_codes, failure_probs = ranges[segment]
        amount = int(self.rng.integers(amount_range[0], amount_range[1] + 1))
        ltv = int(self.rng.integers(ltv_range[0], ltv_range[1] + 1))
        failure_code = str(self.rng.choice(failure_codes, p=failure_probs))
        payment_method = str(self.rng.choice(("upi", "card", "netbanking", "wallet")))
        if segment == "A":
            payment_hour = int(self.rng.integers(19, 22))
        else:
            payment_hour = int(self.rng.integers(0, 24))
        failures = int(self.rng.integers(0, 6))
        successes = int(self.rng.integers(0, 12))
        timestamp = datetime.now(timezone.utc) - timedelta(days=int(self.rng.integers(0, 365)))
        return EventRecord(
            event_id=f"event_{index + 1:06d}", customer_id=customer_id, merchant_id=merchant_id,
            segment=segment, transaction_amount_paise=amount, payment_method=payment_method,
            failure_code=failure_code, failure_category=self.FAILURE_CATEGORIES[failure_code],
            customer_ltv_paise=ltv, previous_successes=successes, previous_failures=failures,
            subscription_age_days=int(self.rng.integers(30, 1_500)),
            days_since_last_payment=float(self.rng.uniform(0.5, 45.0)),
            historical_payment_hour=payment_hour, historical_payment_day=int(self.rng.integers(0, 7)),
            timestamp=timestamp, retry_success_rate=float(self.rng.uniform(0.10, 0.80)),
            whatsapp_success_rate=float(self.rng.uniform(0.10, 0.75)),
            email_success_rate=float(self.rng.uniform(0.08, 0.60)),
            upi_switch_success_rate=float(self.rng.uniform(0.15, 0.85)),
        )

    def _save(self, dataset: GeneratedDataset, n_events: int) -> None:
        output_dir = Path("simulation/data")
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / f"events_{n_events}.json").write_text(
            json.dumps([asdict(event) for event in dataset.events], default=str, indent=2), encoding="utf-8"
        )
        (output_dir / f"customers_{n_events}.json").write_text(
            json.dumps(dataset.customers, indent=2), encoding="utf-8"
        )