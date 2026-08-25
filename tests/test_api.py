"""API tests for the Phase 5 FastAPI backend (live PostgreSQL + Redis)."""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers.analytics import OVERVIEW_KEY, _cache
from db.database import SessionLocal
from db.models import (
    Customer,
    Merchant,
    RecoveryCase,
    RecoveryCaseStatus,
    RecoveryOutcome,
)

client = TestClient(app)


@pytest.fixture(scope="module")
def _client():
    return client


def _make_case(amount_paise: int = 500_000) -> tuple[RecoveryCase, str, str]:
    merchant_id = f"m_{uuid.uuid4().hex[:8]}"
    customer_id = f"c_{uuid.uuid4().hex[:8]}"
    case_id = f"case_{uuid.uuid4().hex[:8]}"
    session = SessionLocal()
    session.add_all(
        [
            Merchant(id=merchant_id, name="Test"),
            Customer(id=customer_id, merchant_id=merchant_id, name="Test"),
            RecoveryCase(
                id=case_id,
                merchant_id=merchant_id,
                customer_id=customer_id,
                amount_at_risk_paise=amount_paise,
                failure_code="INSUFFICIENT_FUNDS",
                priority=100,
                status=RecoveryCaseStatus.NEW.value,
            ),
        ]
    )
    session.commit()
    case = session.get(RecoveryCase, case_id)
    session.close()
    return case, merchant_id, customer_id


def _cleanup(session, case_id: str, merchant_id: str, customer_id: str) -> None:
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


# ---------------------------------------------------------------------------
# Wave 1
# ---------------------------------------------------------------------------


def test_health(_client):
    r = _client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_cases_paginated(_client):
    r = _client.get("/api/recovery/cases", params={"page": 1, "page_size": 5})
    assert r.status_code == 200
    body = r.json()
    assert "items" in body and "total" in body
    assert body["page"] == 1
    for item in body["items"]:
        assert isinstance(item["amount_at_risk_paise"], int)


def test_get_case_detail_404(_client):
    r = _client.get("/api/recovery/cases/does-not-exist")
    assert r.status_code == 404


def test_get_case_detail_timeline(_client):
    case, mid, cid = _make_case()
    try:
        r = _client.get(f"/api/recovery/cases/{case.id}")
        assert r.status_code == 200
        body = r.json()
        assert body["id"] == case.id
        assert isinstance(body["amount_at_risk_paise"], int)
        assert "timeline" in body
    finally:
        session = SessionLocal()
        _cleanup(session, case.id, mid, cid)
        session.close()


def test_analytics_overview_shape(_client):
    r = _client.get("/api/analytics/overview")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["revenue_at_risk_paise"], int)
    assert isinstance(body["recovered_paise"], int)
    assert 0.0 <= body["recovery_rate"] <= 1.0 or body["recovery_rate"] == 0.0
    assert "total_cases" in body


def test_analytics_overview_cached(_client):
    known = {
        "revenue_at_risk_paise": 1234,
        "recovered_paise": 567,
        "recovery_rate": 0.25,
        "total_cases": 3,
        "recovered_cases": 1,
        "executed_at_risk_paise": 0,
        "incremental_paise": None,
    }
    _cache.setex(OVERVIEW_KEY, 30, __import__("json").dumps(known))
    try:
        r = _client.get("/api/analytics/overview")
        assert r.status_code == 200
        assert r.json() == known
    finally:
        _cache.delete(OVERVIEW_KEY)


def test_analytics_strategies(_client):
    r = _client.get("/api/analytics/strategies")
    assert r.status_code == 200
    for row in r.json():
        assert isinstance(row["recovered_paise"], int)
        assert "strategy" in row


# ---------------------------------------------------------------------------
# Wave 2
# ---------------------------------------------------------------------------


def test_risk_score_formula():
    from engine.risk_engine import compute_risk_score

    # 100_000 * 1.0 * 0.5 * 1.0 = 50_000
    assert compute_risk_score(100_000, 1.0, 0.5, 1.0) == 50_000
    assert isinstance(compute_risk_score(100_000, 1.0, 0.5, 1.0), int)


def test_ingest_payment_failed_creates_case(_client):
    merchant_id, customer_id, event_id = (
        f"m_{uuid.uuid4().hex[:8]}",
        f"c_{uuid.uuid4().hex[:8]}",
        f"evt_{uuid.uuid4().hex[:8]}",
    )
    session = SessionLocal()
    session.add_all(
        [
            Merchant(id=merchant_id, name="Test"),
            Customer(id=customer_id, merchant_id=merchant_id, name="Test", lifetime_value_paise=1_000_000),
        ]
    )
    session.commit()
    session.close()
    payload = {
        "event_id": event_id,
        "event_type": "payment.failed",
        "merchant_id": merchant_id,
        "customer_id": customer_id,
        "amount_paise": 250_000,
        "payment_method": "upi",
        "failure_code": "INSUFFICIENT_FUNDS",
    }
    try:
        r = _client.post("/api/events/ingest", json=payload)
        assert r.status_code == 200
        body = r.json()
        assert body["ingested"] is True
        assert body["recovery_case_id"] is not None
        # Idempotent: duplicate event_id is skipped.
        r2 = _client.post("/api/events/ingest", json=payload)
        assert r2.json()["duplicate"] is True
        assert r2.json()["ingested"] is False
    finally:
        session = SessionLocal()
        from db.models import Payment

        case = session.query(RecoveryCase).filter_by(source_id=event_id).first()
        if case:
            session.query(RecoveryOutcome).filter_by(case_id=case.id).delete()
            session.delete(case)
        payment = session.get(Payment, event_id)
        if payment:
            session.delete(payment)
        session.commit()
        session.close()
        session = SessionLocal()
        c = session.get(Customer, customer_id)
        if c:
            session.delete(c)
        m = session.get(Merchant, merchant_id)
        if m:
            session.delete(m)
        session.commit()
        session.close()


def test_ingest_unsupported_type_rejected(_client):
    r = _client.post(
        "/api/events/ingest",
        json={
            "event_id": "x",
            "event_type": "bogus.type",
            "merchant_id": "m",
            "customer_id": "c",
            "amount_paise": 100,
        },
    )
    assert r.status_code == 400  # unsupported event_type rejected


def test_simulation_run_eager():
    from agents.tasks import run_simulation

    result = run_simulation.apply(args=[20, 42, 14]).get()
    assert result["baseline"]["total_events"] == 20
    assert result["razor"]["total_events"] == 20
    assert isinstance(result["incremental_paise"], int)


def test_experiments_endpoint(_client):
    r = _client.get("/api/experiments")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

