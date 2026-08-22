"""Populate the DB with a realistic recovery run so the dashboard tells the demo story.

Creates merchant + customers + failed payments, runs the decision engine per case
(decisions + audit logs), executes + verifies outcomes (recovery_outcomes), and
updates recovery memory / customer profiles. After running, the dashboard's
Overview, Recovery Queue, Strategy, Agent Activity, and drill-down all show real data.

Usage:
    python scripts/demo_data.py --events 800 [--reset] [--hour 14]

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
from engine.decision_engine import DecisionEngine
from engine.outcome_verifier import ActionExecutor, OutcomeVerifier
from engine.recovery_memory import record_outcome, update_profile
from engine.risk_engine import build_severity, compute_risk_score, customer_value_factor
from ml.recovery_model import RecoveryModel
from simulation.generator import SyntheticDataGenerator

EXECUTABLE = {
    "RETRY",
    "PAYMENT_METHOD_SWITCH",
    "WHATSAPP_REMINDER",
    "EMAIL_REMINDER",
    "DISCOUNT_OFFER",
    "PAYMENT_LINK",
    "HUMAN_ESCALATION",
}
DEFAULT_PROB = 0.4


def _features(event, profile):
    return {
        "transaction_amount_paise": event.transaction_amount_paise,
        "payment_method": event.payment_method,
        "failure_code": event.failure_code,
        "customer_ltv_paise": event.customer_ltv_paise,
        "previous_successes": event.previous_successes,
        "previous_failures": event.previous_failures,
        "time_since_last_payment_days": event.days_since_last_payment,
        "historical_payment_hour": event.historical_payment_hour,
        "historical_payment_day": event.historical_payment_day,
        "previous_strategy": "RETRY",
        "previous_strategy_success_rate": event.retry_success_rate,
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
    parser = argparse.ArgumentParser(description="Populate demo recovery data.")
    parser.add_argument("--events", type=int, default=800)
    parser.add_argument("--hour", type=int, default=14)
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    model = RecoveryModel.load("ml/artifacts/recovery_model.joblib")
    engine = DecisionEngine(model)
    verifier = OutcomeVerifier(ActionExecutor(seed=args.seed))

    print(f"Generating {args.events} events...")
    dataset = SyntheticDataGenerator(seed=args.seed).generate(args.events)

    session = SessionLocal()
    try:
        if args.reset:
            reset_tables(session)

        merchant = Merchant(id="merchant_001", name="Demo Merchant")
        session.merge(merchant)

        cases = 0
        recovered_cases = 0
        total_recovered = 0
        for event, cust, prof in zip(dataset.events, dataset.customers, dataset.profiles):
            customer = Customer(
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
            session.merge(customer)
            profile = CustomerRecoveryProfile(
                customer_id=event.customer_id,
                merchant_id="merchant_001",
                overall_recovery_probability=event.retry_success_rate,
            )
            session.merge(profile)

            payment = Payment(
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
            session.merge(payment)

            severity = build_severity(event.failure_code)
            value_factor = customer_value_factor(event.customer_ltv_paise)
            risk = compute_risk_score(
                event.transaction_amount_paise, severity, event.retry_success_rate, value_factor
            )
            case = RecoveryCase(
                id=f"rc_{event.event_id}",
                merchant_id="merchant_001",
                customer_id=event.customer_id,
                source_type="payment",
                source_id=event.event_id,
                amount_at_risk_paise=event.transaction_amount_paise,
                failure_code=event.failure_code,
                failure_reason=event.failure_category,
                priority=risk,
                status="NEW",
            )
            case = session.merge(case)
            session.commit()

            feats = _features(event, profile)
            decision = engine.decide(case, feats, current_hour=args.hour)
            cases += 1

            strategy = decision.selected_strategy
            if strategy in EXECUTABLE:
                outcome = verifier.verify(case, event.segment, strategy, event.transaction_amount_paise)
                record_outcome(
                    session,
                    event.customer_id,
                    event.failure_code,
                    strategy,
                    outcome.net_revenue_recovered_paise > 0 and "RECOVERED" or "FAILED",
                    outcome.revenue_recovered_paise > 0,
                    event.transaction_amount_paise,
                )
                if outcome.revenue_recovered_paise > 0:
                    recovered_cases += 1
                    total_recovered += outcome.revenue_recovered_paise
                session.commit()
                update_profile(session, event.customer_id)
            # WAIT/STOP: no outcome recorded; case stays STRATEGY_SELECTED / STOPPED.

        print(f"Done: {cases} cases, {recovered_cases} recovered, ₹{total_recovered/100:,.0f} recovered")
        print("Dashboard now shows a populated Overview, Queue, Strategy, and drill-downs.")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
