"""FR-11 recovery memory: record outcomes and recompute customer profiles."""
from __future__ import annotations

from sqlalchemy.orm import Session

from db.models import Customer, CustomerRecoveryProfile, RecoveryMemory

# Map a recovery strategy to the CustomerRecoveryProfile channel it updates.
STRATEGY_CHANNEL: dict[str, str] = {
    "RETRY": "retry",
    "PAYMENT_METHOD_SWITCH": "upi_switch",
    "WHATSAPP_REMINDER": "whatsapp",
    "EMAIL_REMINDER": "email",
    "DISCOUNT_OFFER": "discount",
}

CHANNELS = ("retry", "upi_switch", "whatsapp", "email", "discount")


def record_outcome(
    session: Session,
    customer_id: str,
    failure_type: str | None,
    strategy: str,
    outcome: str,
    recovered: bool,
    amount_paise: int,
) -> RecoveryMemory:
    """Store one (customer, failure_type, strategy, outcome) learning tuple."""
    memory = RecoveryMemory(
        customer_id=customer_id,
        failure_type=failure_type,
        strategy=strategy,
        outcome=outcome,
        recovered=bool(recovered),
        amount_paise=int(amount_paise),
    )
    session.add(memory)
    session.flush()
    return memory


def update_profile(session: Session, customer_id: str) -> CustomerRecoveryProfile | None:
    """Recompute a customer's per-channel success rates from recovery memory.

    Deterministic: attempts/successes per channel and overall recovery
    probability (successes/attempts, default 0.5 when no data).
    """
    customer = session.get(Customer, customer_id)
    if customer is None:
        return None

    session.expire_on_commit = False
    rows = session.query(RecoveryMemory).filter(RecoveryMemory.customer_id == customer_id).all()
    stats = {ch: {"attempts": 0, "successes": 0} for ch in CHANNELS}
    total_attempts = 0
    total_successes = 0
    for row in rows:
        channel = STRATEGY_CHANNEL.get(row.strategy)
        if channel is None:
            continue
        stats[channel]["attempts"] += 1
        total_attempts += 1
        if row.recovered:
            stats[channel]["successes"] += 1
            total_successes += 1

    profile = (
        session.query(CustomerRecoveryProfile)
        .filter(CustomerRecoveryProfile.customer_id == customer_id)
        .first()
    )
    if profile is None:
        profile = CustomerRecoveryProfile(
            customer_id=customer_id,
            merchant_id=customer.merchant_id,
        )
        session.add(profile)

    for channel, counts in stats.items():
        setattr(profile, f"{channel}_attempts", counts["attempts"])
        setattr(profile, f"{channel}_successes", counts["successes"])
    profile.overall_recovery_probability = (
        total_successes / total_attempts if total_attempts else 0.5
    )
    session.commit()
    return profile
