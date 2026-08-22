"""Seed-DB demo CLI for the RAZOR decision engine + policy guardrails.

Loads seeded recovery cases, runs the decision engine and policy hard gate, and
prints per-case decisions. Demonstrates AC-04 (WAIT selected when a future
window is better) and AC-05 (policy blocks a discount exceeding
max_discount_percent). All decisions are logged to PostgreSQL (AC-08).
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
    Payment,
    RecoveryCase,
    RecoveryCaseStatus,
)
from engine.decision_engine import Decision, DecisionEngine
from engine.policy_engine import PolicyEngine, load_policy_yaml
from ml.recovery_model import RecoveryModel


def _ensure_seed(session) -> None:
    """Seed the DB with failed payments if it is empty."""
    if session.query(Payment).count() > 0:
        return
    print("Seeding demo database (no payments found)...")
    import scripts.seed_db as seed_db

    seed_db.seed()


def _create_cases(session, limit: int) -> int:
    """Create one recovery case per failed payment if none exist yet."""
    if session.query(RecoveryCase).count() > 0:
        return 0
    payments = (
        session.query(Payment)
        .filter(Payment.status == "FAILED")
        .limit(limit)
        .all()
    )
    for payment in payments:
        session.add(
            RecoveryCase(
                merchant_id=payment.merchant_id,
                customer_id=payment.customer_id,
                source_type="payment",
                source_id=payment.id,
                amount_at_risk_paise=payment.amount_paise,
                failure_code=payment.failure_code,
                failure_reason=payment.failure_reason,
                status=RecoveryCaseStatus.NEW.value,
            )
        )
    session.commit()
    return len(payments)


def _features(payment: Payment | None, customer: Customer | None, profile: CustomerRecoveryProfile | None) -> dict:
    return {
        "transaction_amount_paise": payment.amount_paise if payment else 100_000,
        "payment_method": (payment.payment_method if payment and payment.payment_method else "upi"),
        "failure_code": (payment.failure_code if payment and payment.failure_code else "INSUFFICIENT_FUNDS"),
        "customer_ltv_paise": customer.lifetime_value_paise if customer else 0,
        "previous_successes": profile.retry_successes if profile else 0,
        "previous_failures": profile.retry_attempts if profile else 0,
        "time_since_last_payment_days": 5.0,
        "historical_payment_hour": (customer.typical_payment_hour_start if customer and customer.typical_payment_hour_start is not None else 14),
        "historical_payment_day": 2,
        "previous_strategy": "RETRY",
        "previous_strategy_success_rate": (profile.overall_recovery_probability if profile else 0.4),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RAZOR decision-engine demo (seed DB + CLI).")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--policy", default="engine/policies/merchant_001.yaml")
    parser.add_argument("--model", default="ml/artifacts/recovery_model.joblib")
    parser.add_argument("--hour", type=int, default=10, help="Current hour (default 10, outside the 19-22 window -> WAIT).")
    args = parser.parse_args(argv)

    policy = load_policy_yaml(args.policy)
    model = RecoveryModel.load(args.model)
    engine = DecisionEngine(model, wait_window=policy.wait_window)
    policy_engine = PolicyEngine(policy)
    demo_discount_rate = 0.25  # above max_discount_percent (10%) -> AC-05

    session = SessionLocal()
    try:
        _ensure_seed(session)
        _create_cases(session, args.limit)
        cases = session.query(RecoveryCase).limit(args.limit).all()

        print("=" * 78)
        print("RAZOR Decision Engine demo (simulator-only, offline)")
        print(f"policy={args.policy}  current_hour={args.hour}  wait_window={policy.wait_window}")
        print("=" * 78)
        print(f"{'case_id':<10} {'amount':>10} {'strategy':<20} {'exp_net':>10}  {'policy':<16}  reasoning")
        wait_count = 0
        block_count = 0
        for case in cases:
            payment = session.get(Payment, case.source_id) if case.source_id else None
            customer = session.get(Customer, case.customer_id)
            profile = (
                session.query(CustomerRecoveryProfile)
                .filter_by(customer_id=case.customer_id)
                .first()
            )
            feats = _features(payment, customer, profile)
            decision = engine.decide(
                case, feats, current_hour=args.hour, discount_rate=policy.max_discount_rate
            )
            pres = policy_engine.check(
                decision, case.amount_at_risk_paise, discount_rate=policy.max_discount_rate
            )
            if decision.selected_strategy == "WAIT":
                wait_count += 1
            if pres.status == "BLOCK":
                block_count += 1
            print(
                f"{case.id:<10} {case.amount_at_risk_paise:>10} "
                f"{decision.selected_strategy:<20} {decision.expected_net_recovery_paise:>10}  "
                f"{pres.status:<16} {decision.reasoning[:44]}"
            )

        # AC-04 marker
        print()
        print(f"AC-04: {wait_count} case(s) selected WAIT (future window EV > now)")

        # AC-05 explicit guardrail demonstration: discount above max is blocked.
        print()
        print("AC-05: policy hard gate on DISCOUNT_OFFER")
        demo_decision = Decision(
            case_id="demo",
            candidate_strategy="DISCOUNT_OFFER",
            selected_strategy="DISCOUNT_OFFER",
            expected_net_recovery_paise=0,
            reasoning="demo discount offer",
            policy_check_passed=None,
            recommended_at=None,
            status="STRATEGY_SELECTED",
        )
        blocked = policy_engine.check(
            demo_decision, 500_000, discount_rate=demo_discount_rate
        )
        print(
            f"  DISCOUNT_OFFER @ {demo_discount_rate:.0%} "
            f"(max {policy.max_discount_percent}%) -> {blocked.status}: {blocked.reason}"
        )
        passed = policy_engine.check(
            demo_decision, 500_000, discount_rate=policy.max_discount_rate
        )
        print(
            f"  DISCOUNT_OFFER @ {policy.max_discount_rate:.0%} "
            f"(<= max {policy.max_discount_percent}%) -> {passed.status}"
        )
        print()
        print("All decisions + audit rows written to PostgreSQL (AC-08).")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
