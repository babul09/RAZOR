"""Minimal operator-console contract tests (payment limits + approvals + action)."""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from api.main import app
from db.database import SessionLocal
from db.models import (
    Customer,
    Merchant,
    Payment,
    RecoveryCase,
    RecoveryCaseStatus,
    AgentDecision,
    AuditLog,
    RecoveryOutcome,
    RecoveryAction,
    RecoveryMemory,
)

client = TestClient(app)
MERCHANT = "merchant_001"


@pytest.fixture(scope="module", autouse=True)
def _cleanup_operator_cases():
    yield
    session = SessionLocal()
    ids = [
        r[0]
        for r in session.query(RecoveryCase.id)
        .filter(RecoveryCase.id.like("op_%"))
        .all()
    ]
    for m in (RecoveryOutcome, RecoveryAction, AgentDecision, AuditLog):
        session.query(m).filter(m.case_id.in_(ids)).delete(synchronize_session=False)
    session.query(RecoveryCase).filter(RecoveryCase.id.in_(ids)).delete(synchronize_session=False)
    session.commit()
    session.close()


def _seed_case() -> dict:
    session = SessionLocal()
    cid = f"c_{uuid.uuid4().hex[:8]}"
    eid = f"e_{uuid.uuid4().hex[:8]}"
    case_id = f"op_{uuid.uuid4().hex[:8]}"
    if not session.get(Merchant, MERCHANT):
        session.add(Merchant(id=MERCHANT, name="Demo"))
    session.merge(Customer(id=cid, merchant_id=MERCHANT, name="T", lifetime_value_paise=1_000_000, customer_segment="C"))
    session.merge(Payment(id=eid, merchant_id=MERCHANT, customer_id=cid, amount_paise=100_000, status="FAILED", failure_code="INSUFFICIENT_FUNDS"))
    session.merge(RecoveryCase(id=case_id, merchant_id=MERCHANT, customer_id=cid, source_type="payment", source_id=eid, amount_at_risk_paise=100_000, failure_code="INSUFFICIENT_FUNDS", status=RecoveryCaseStatus.NEW.value))
    session.commit()
    session.close()
    return {"case_id": case_id, "cid": cid, "eid": eid}


def test_policy_get_and_update():
    r = client.get("/api/policy")
    assert r.status_code == 200
    body = r.json()
    assert body["merchant_id"] == MERCHANT
    assert isinstance(body["max_automated_amount_paise"], int)

    r = client.put("/api/policy", json={"max_automated_amount_paise": 2_000_000, "max_discount_percent": 15})
    assert r.status_code == 200
    assert r.json()["max_automated_amount_paise"] == 2_000_000
    assert r.json()["max_discount_percent"] == 15

    # Persisted — a fresh GET reflects it.
    assert client.get("/api/policy").json()["max_automated_amount_paise"] == 2_000_000


def test_action_blocks_when_limit_exceeded_then_approve_executes():
    ref = _seed_case()
    case_id = ref["case_id"]
    try:
        client.put("/api/policy", json={"max_automated_amount_paise": 10_000})

        blocked = client.post(f"/api/recovery/cases/{case_id}/action", json={"strategy": "RETRY"})
        assert blocked.status_code == 200
        assert blocked.json()["executed"] is False
        assert blocked.json()["status"] == "AWAITING_APPROVAL"

        client.put("/api/policy", json={"max_automated_amount_paise": 500_000})
        approved = client.post(f"/api/recovery/cases/{case_id}/approve")
        assert approved.status_code == 200
        assert approved.json()["executed"] is True
        assert approved.json()["status"] in ("RECOVERED", "FAILED")

        session = SessionLocal()
        try:
            case = session.get(RecoveryCase, case_id)
            assert session.query(RecoveryOutcome).filter_by(case_id=case.id).count() == 1
            assert session.query(AgentDecision).filter_by(case_id=case.id).count() >= 1
        finally:
            session.close()
    finally:
        session = SessionLocal()
        for m in (AgentDecision, AuditLog, RecoveryOutcome, RecoveryAction):
            session.query(m).filter_by(case_id=case_id).delete()
        session.query(RecoveryMemory).filter_by(customer_id=ref["cid"]).delete()
        case = session.get(RecoveryCase, case_id)
        if case:
            session.delete(case)
        session.delete(session.get(Payment, ref["eid"]))
        session.delete(session.get(Customer, ref["cid"]))
        session.commit()
        session.close()


def test_reject_routes_to_stopped():
    ref = _seed_case()
    case_id = ref["case_id"]
    try:
        client.put("/api/policy", json={"max_automated_amount_paise": 10_000})
        client.post(f"/api/recovery/cases/{case_id}/action", json={"strategy": "RETRY"})

        r = client.post(f"/api/recovery/cases/{case_id}/reject")
        assert r.status_code == 200
        assert r.json()["status"] == "STOPPED"
        assert r.json()["executed"] is False
    finally:
        session = SessionLocal()
        for m in (AgentDecision, AuditLog, RecoveryOutcome, RecoveryAction):
            session.query(m).filter_by(case_id=case_id).delete()
        session.query(RecoveryMemory).filter_by(customer_id=ref["cid"]).delete()
        case = session.get(RecoveryCase, case_id)
        if case:
            session.delete(case)
        session.delete(session.get(Payment, ref["eid"]))
        session.delete(session.get(Customer, ref["cid"]))
        session.commit()
        session.close()
