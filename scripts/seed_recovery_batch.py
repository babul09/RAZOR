"""Seed the demo DB across all four revenue-at-risk event types and execute a
measured recovery batch so the dashboard tells the full story.

Populates a merchant + customers + failed revenue events spread across
payment, checkout, subscription, and invoice — then runs the RAZOR batch
executor (decision -> policy hard gate -> action execution -> measured outcome)
so the Overview headline, Recovery Queue, Architecture pipeline, Strategy, and
drill-downs all show live, executed data.

Usage:
    python scripts/seed_recovery_batch.py --events 600 [--reset] [--hour 14]

--reset clears prior recovery/payment rows first (keeps the demo clean/repeatable).
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import SessionLocal
from db.models import (
    Customer,
    CustomerRecoveryProfile,
    Merchant,
    Payment,
    RecoveryCase,
)
from engine.policy_engine import MerchantPolicy, load_policy_yaml
from engine.recovery_batch import RecoveryBatchExecutor, SOURCE_TYPES
from engine.risk_engine import build_severity, compute_risk_score, customer_value_factor
from ml.recovery_model import RecoveryModel
from simulation.generator import SyntheticDataGenerator

# Segment -> revenue-risk event type, giving breadth across all four.
EVENT_TYPE_BY_SEGMENT = {
    "A": "payment.failed",
    "B": "subscription.failed",
    "C": "checkout.abandoned",
    "D": "payment.failed",
    "E": "invoice.overdue",
}


def reset_tables(session) -> None:
    from db.models import (
        AgentDecision,
        AuditLog,
        Experiment,
        ExperimentArm,
        Policy,
        RecoveryAction,
        RecoveryMemory,
        RecoveryOutcome,
    )

    session.query(ExperimentArm).delete()
    session.query(Experiment).delete()
    session.query(Policy).delete()
    for m in (AgentDecision, AuditLog, RecoveryOutcome, RecoveryAction, RecoveryMemory):
        session.query(m).delete()
    session.query(RecoveryCase).delete()
    session.query(Payment).delete()
    session.query(CustomerRecoveryProfile).delete()
    session.query(Customer).delete()
    session.query(Merchant).delete()
    session.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed + execute a measured recovery batch.")
    parser.add_argument("--events", type=int, default=120)
    parser.add_argument("--hour", type=int, default=20, help="In-window hour so cases execute (19-22).")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--policy", default="engine/policies/merchant_001.yaml")
    args = parser.parse_args()

    model = RecoveryModel.load("ml/artifacts/recovery_model.joblib")
    try:
        policy = load_policy_yaml(args.policy)
    except Exception:
        policy = MerchantPolicy(merchant_id="merchant_001")

    print(f"Generating {args.events} events across all four revenue-risk types...")
    dataset = SyntheticDataGenerator(seed=args.seed).generate(args.events)

    session = SessionLocal()
    try:
        if args.reset:
            reset_tables(session)

        merchant = Merchant(id="merchant_001", name="Demo Merchant")
        session.merge(merchant)

        for event, cust, prof in zip(dataset.events, dataset.customers, dataset.profiles):
            event_type = EVENT_TYPE_BY_SEGMENT[event.segment]
            source_type = event_type.split(".")[0]

            session.merge(
                Customer(
                    id=cust["id"],
                    merchant_id="merchant_001",
                    name=cust["name"],
                    email=cust.get("email"),
                    phone=cust.get("phone"),
                    lifetime_value_paise=cust["lifetime_value_paise"],
                    preferred_payment_method=cust.get("preferred_payment_method"),
                    typical_payment_hour_start=cust.get("typical_payment_hour_start"),
                    typical_payment_hour_end=cust.get("typical_payment_hour_end"),
                    customer_segment=event.segment,
                )
            )
            session.merge(
                CustomerRecoveryProfile(
                    customer_id=event.customer_id,
                    merchant_id="merchant_001",
                    overall_recovery_probability=event.retry_success_rate,
                )
            )
            session.merge(
                Payment(
                    id=event.event_id,
                    merchant_id="merchant_001",
                    customer_id=event.customer_id,
                    amount_paise=event.transaction_amount_paise,
                    currency="INR",
                    payment_method=event.payment_method,
                    status="FAILED",
                    failure_code=event.failure_code,
                    failure_reason=event.failure_category,
                )
            )

            severity = build_severity(event.failure_code)
            value_factor = customer_value_factor(event.customer_ltv_paise)
            risk = compute_risk_score(
                event.transaction_amount_paise, severity, event.retry_success_rate, value_factor
            )
            session.merge(
                RecoveryCase(
                    id=f"rc_{event.event_id}",
                    merchant_id="merchant_001",
                    customer_id=event.customer_id,
                    source_type=source_type,
                    source_id=event.event_id,
                    amount_at_risk_paise=event.transaction_amount_paise,
                    failure_code=event.failure_code,
                    failure_reason=event.failure_category,
                    priority=risk,
                    status="NEW",
                )
            )
        session.commit()
    finally:
        session.close()

    print("Executing recovery batch (all four event types)...")
    executor = RecoveryBatchExecutor(model, policy, current_hour=args.hour, seed=args.seed)
    result = executor.run(source_types=list(SOURCE_TYPES), limit=args.events)

    print(f"\nSeeded {result.processed_cases} cases across {len(result.per_source)} event types:")
    for m in result.per_source:
        print(
            f"  {m.source_type:<12} processed={m.processed:<4} attempts={m.attempts:<4} "
            f"recoveries={m.recoveries:<4} recovered=₹{m.recovered_paise / 100:,.0f}"
        )
    print(
        f"\nTotal executed: {result.executed} | recovered: {result.recoveries} | "
        f"measured incremental: ₹{result.incremental_paise / 100:,.0f}"
    )
    print("\nDashboard now shows a populated How-it-works, Overview, Architecture, Queue, Strategy, and drill-downs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
