"""DB-backed tests for the Phase 6 recovery memory + weighted EV."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine, inspect

from config import settings
from db.database import SessionLocal
from db.models import (
    Customer,
    CustomerRecoveryProfile,
    Merchant,
    RecoveryCase,
    RecoveryCaseStatus,
    RecoveryMemory,
)
from engine.decision_engine import DecisionEngine
from engine.recovery_memory import record_outcome, update_profile
from ml.recovery_model import RecoveryModel


@pytest.fixture(scope="module")
def model():
    return RecoveryModel.load("ml/artifacts/recovery_model.joblib")


def _make_customer() -> tuple[str, str]:
    merchant_id = f"m_{uuid.uuid4().hex[:8]}"
    customer_id = f"c_{uuid.uuid4().hex[:8]}"
    session = SessionLocal()
    session.add_all(
        [
            Merchant(id=merchant_id, name="Test"),
            Customer(id=customer_id, merchant_id=merchant_id, name="Test"),
        ]
    )
    session.commit()
    session.close()
    return merchant_id, customer_id


def _cleanup(merchant_id: str, customer_id: str) -> None:
    session = SessionLocal()
    session.query(RecoveryMemory).filter_by(customer_id=customer_id).delete()
    profile = (
        session.query(CustomerRecoveryProfile).filter_by(customer_id=customer_id).first()
    )
    if profile:
        session.delete(profile)
    customer = session.get(Customer, customer_id)
    if customer:
        session.delete(customer)
    merchant = session.get(Merchant, merchant_id)
    if merchant:
        session.delete(merchant)
    session.commit()
    session.close()


def _features():
    from ml.training import FEATURE_COLUMNS, build_training_frame
    from simulation.generator import SyntheticDataGenerator

    events = SyntheticDataGenerator(seed=42).generate(20).events
    row = build_training_frame(events, seed=42).iloc[0]
    return {k: row[k] for k in FEATURE_COLUMNS if k != "candidate_strategy"}


# ---------------------------------------------------------------------------
# Wave 1
# ---------------------------------------------------------------------------


def test_recovery_memory_table_exists():
    engine = create_engine(settings.database_url)
    assert "recovery_memory" in inspect(engine).get_table_names()


def test_record_outcome_stores_row():
    merchant_id, customer_id = _make_customer()
    try:
        session = SessionLocal()
        mem = record_outcome(
            session,
            customer_id,
            "INSUFFICIENT_FUNDS",
            "RETRY",
            "RECOVERED",
            True,
            100_000,
        )
        memory_id = mem.id
        session.commit()
        session.close()
        session = SessionLocal()
        row = session.query(RecoveryMemory).filter_by(id=memory_id).first()
        session.close()
        assert row is not None
        assert row.customer_id == customer_id
        assert row.strategy == "RETRY"
        assert row.recovered is True
    finally:
        _cleanup(merchant_id, customer_id)


def test_update_profile_recomputes():
    merchant_id, customer_id = _make_customer()
    try:
        session = SessionLocal()
        record_outcome(session, customer_id, "IF", "RETRY", "RECOVERED", True, 100_000)
        record_outcome(session, customer_id, "IF", "RETRY", "FAILED", False, 100_000)
        record_outcome(session, customer_id, "IF", "WHATSAPP_REMINDER", "RECOVERED", True, 100_000)
        session.commit()
        profile = update_profile(session, customer_id)
        session.close()
        assert profile is not None
        assert profile.retry_attempts == 2
        assert profile.retry_successes == 1
        assert profile.whatsapp_attempts == 1
        assert profile.whatsapp_successes == 1
        assert profile.overall_recovery_probability == pytest.approx(2 / 3)
    finally:
        _cleanup(merchant_id, customer_id)


def test_strategy_weight_scales_ev(model):
    eng_neutral = DecisionEngine(model)
    eng_weighted = DecisionEngine(model)
    eng_weighted.set_strategy_weights({"RETRY": 2.0})
    feats = _features()
    neutral = eng_neutral.expected_net_recovery(feats, "RETRY", 500_000)
    weighted = eng_weighted.expected_net_recovery(feats, "RETRY", 500_000)
    assert weighted > neutral  # higher weight -> higher EV (before clamp)
    # Weight is clamped: probability stays in [0,1], EV bounded by amount.
    assert weighted <= 500_000


def test_update_profile_task_eager():
    from agents.tasks import update_profile as task

    merchant_id, customer_id = _make_customer()
    try:
        session = SessionLocal()
        record_outcome(session, customer_id, "IF", "EMAIL_REMINDER", "RECOVERED", True, 50_000)
        session.commit()
        session.close()
        result = task.apply(args=[customer_id]).get()
        assert result["ok"] is True
        assert result["overall_recovery_probability"] == pytest.approx(1.0)
    finally:
        _cleanup(merchant_id, customer_id)
