#!/usr/bin/env python3
"""Seed the demo PostgreSQL database from deterministic synthetic events."""
from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert as pg_insert

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import SessionLocal
from db.models import Customer, CustomerRecoveryProfile, Merchant, Payment, Policy
from simulation.generator import SyntheticDataGenerator


def seed() -> None:
    dataset = SyntheticDataGenerator(seed=42).generate(20_000)
    customer_rows = dataset.customers
    payment_rows = [
        {
            "id": event.event_id,
            "merchant_id": event.merchant_id,
            "customer_id": event.customer_id,
            "amount_paise": event.transaction_amount_paise,
            "currency": "INR",
            "payment_method": event.payment_method,
            "status": "FAILED",
            "failure_code": event.failure_code,
            "failure_reason": event.failure_category,
        }
        for event in dataset.events
    ]
    profile_rows = dataset.profiles
    with SessionLocal.begin() as session:
        inserted = {}
        for model, rows in (
            (Merchant, [{"id": "merchant_001", "name": "Demo Merchant"}]),
            (Customer, customer_rows),
            (Payment, payment_rows),
            (CustomerRecoveryProfile, profile_rows),
            (Policy, [{"merchant_id": "merchant_001"}]),
        ):
            statement = pg_insert(model).values(rows).on_conflict_do_nothing()
            result = session.execute(statement)
            inserted[model.__tablename__] = result.rowcount
    for table, count in inserted.items():
        print(f"{table}: {count} new rows")


if __name__ == "__main__":
    seed()