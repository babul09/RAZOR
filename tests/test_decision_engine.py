"""DB-backed unit tests for the Phase 3 decision engine and state machine."""
from __future__ import annotations

import uuid

import pytest

from db.database import SessionLocal
from db.models import (
    AgentDecision,
    AuditLog,
    Customer,
    Merchant,
    RecoveryCase,
    RecoveryCaseStatus,
)
from engine.decision_engine import DecisionEngine
from engine.state_machine import RecoveryStateMachine, StateEvent, _TRANSITIONS
from ml.recovery_model import RecoveryModel
from ml.training import FEATURE_COLUMNS, build_training_frame
from simulation.generator import SyntheticDataGenerator
from simulation.razor_simulator import STRATEGY_COSTS_PAISE


@pytest.fixture(scope="module")
def model():
    return RecoveryModel.load("ml/artifacts/recovery_model.joblib")


@pytest.fixture(scope="module")
def features():
    events = SyntheticDataGenerator(seed=42).generate(20).events
    row = build_training_frame(events, seed=42).iloc[0]
    return {k: row[k] for k in FEATURE_COLUMNS if k != "candidate_strategy"}


def _cleanup(session, case_id: str, merchant_id: str, customer_id: str) -> None:
    session.query(AgentDecision).filter_by(case_id=case_id).delete()
    session.query(AuditLog).filter_by(case_id=case_id).delete()
    case = session.get(RecoveryCase, case_id)
    if case:
        session.delete(case)
    customer = session.get(Customer, customer_id)
    if customer:
        session.delete(customer)
    merchant = session.get(Merchant, merchant_id)
    if merchant:
        session.delete(merchant)
    session.commit()


def _make_case(amount_paise: int) -> tuple[RecoveryCase, str, str]:
    merchant_id = f"m_{uuid.uuid4().hex[:8]}"
    customer_id = f"c_{uuid.uuid4().hex[:8]}"
    case_id = f"case_{uuid.uuid4().hex[:8]}"
    session = SessionLocal()
    session.add_all(
        [
            Merchant(id=merchant_id, name="Test Merchant"),
            Customer(id=customer_id, merchant_id=merchant_id, name="Test Customer"),
            RecoveryCase(
                id=case_id,
                merchant_id=merchant_id,
                customer_id=customer_id,
                amount_at_risk_paise=amount_paise,
                status=RecoveryCaseStatus.NEW.value,
            ),
        ]
    )
    session.commit()
    case = session.get(RecoveryCase, case_id)
    session.close()
    return case, merchant_id, customer_id


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------


def test_state_machine_transitions():
    sm = RecoveryStateMachine()
    assert _TRANSITIONS
    for (status, event), to in _TRANSITIONS.items():
        assert sm.next_status(status, event) == to
    with pytest.raises(ValueError):
        sm.next_status(RecoveryCaseStatus.RECOVERED, StateEvent.DIAGNOSED)
    assert sm.is_terminal(RecoveryCaseStatus.RECOVERED)
    assert sm.is_terminal(RecoveryCaseStatus.STOPPED)
    assert not sm.is_terminal(RecoveryCaseStatus.NEW)


# ---------------------------------------------------------------------------
# Decision engine
# ---------------------------------------------------------------------------


def test_expected_net_recovery_paise(model, features):
    eng = DecisionEngine(model)
    amount = 500_000
    p = model.predict_proba(features, "RETRY")
    expected = int(p * amount) - STRATEGY_COSTS_PAISE["RETRY"]
    got = eng.expected_net_recovery(features, "RETRY", amount)
    assert isinstance(got, int)
    assert got == expected


def test_decide_persists_decision_and_audit(model, features):
    case, merchant_id, customer_id = _make_case(500_000)
    try:
        eng = DecisionEngine(model)
        decision = eng.decide(case, features, current_hour=14)
        assert decision.case_id == case.id
        assert decision.selected_strategy in (
            "RETRY",
            "PAYMENT_METHOD_SWITCH",
            "WHATSAPP_REMINDER",
            "EMAIL_REMINDER",
            "DISCOUNT_OFFER",
            "PAYMENT_LINK",
            "HUMAN_ESCALATION",
            "WAIT",
            "STOP",
        )
        session = SessionLocal()
        ads = session.query(AgentDecision).filter_by(case_id=case.id).count()
        logs = session.query(AuditLog).filter_by(case_id=case.id).count()
        status = session.get(RecoveryCase, case.id).status
        session.close()
        assert ads == 1
        assert logs == 1
        assert status == RecoveryCaseStatus.STRATEGY_SELECTED.value
    finally:
        session = SessionLocal()
        _cleanup(session, case.id, merchant_id, customer_id)
        session.close()


def test_stop_when_negative_ev(model, features):
    case, merchant_id, customer_id = _make_case(50)  # tiny amount -> all EV < 0
    try:
        eng = DecisionEngine(model)
        decision = eng.decide(case, features, current_hour=14)
        assert decision.selected_strategy == "STOP"
        session = SessionLocal()
        status = session.get(RecoveryCase, case.id).status
        session.close()
        assert status == RecoveryCaseStatus.STOPPED.value
    finally:
        session = SessionLocal()
        _cleanup(session, case.id, merchant_id, customer_id)
        session.close()


def test_wait_when_future_better(model, features):
    # Outside the 19-22 window; RETRY prob at hour 19 (0.73) beats hour 2 (0.615).
    wait_features = dict(features)
    wait_features["historical_payment_hour"] = 2
    case, merchant_id, customer_id = _make_case(500_000)
    try:
        eng = DecisionEngine(model, wait_window=(19, 22))
        decision = eng.decide(case, wait_features, current_hour=2)
        assert decision.selected_strategy == "WAIT"
        assert decision.recommended_at is not None
        session = SessionLocal()
        ads = session.query(AgentDecision).filter_by(case_id=case.id).count()
        logs = session.query(AuditLog).filter_by(case_id=case.id).count()
        session.close()
        assert ads == 1
        assert logs == 1
    finally:
        session = SessionLocal()
        _cleanup(session, case.id, merchant_id, customer_id)
        session.close()
