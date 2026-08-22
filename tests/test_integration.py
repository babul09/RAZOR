"""End-to-end integration test (live DB, eager simulation) + error-shape tests."""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from api.main import app
from db.database import SessionLocal
from db.models import (
    AuditLog,
    Customer,
    Merchant,
    RecoveryCase,
)
from engine.decision_engine import DecisionEngine
from ml.recovery_model import RecoveryModel
from ml.training import FEATURE_COLUMNS, build_training_frame
from simulation.generator import SyntheticDataGenerator

client = TestClient(app)


def _features(events):
    row = build_training_frame(events, seed=42).iloc[0]
    return {k: row[k] for k in FEATURE_COLUMNS if k != "candidate_strategy"}


def _make_merchant_customer() -> tuple[str, str]:
    mid = f"m_{uuid.uuid4().hex[:8]}"
    cid = f"c_{uuid.uuid4().hex[:8]}"
    session = SessionLocal()
    session.add_all(
        [
            Merchant(id=mid, name="Test"),
            Customer(id=cid, merchant_id=mid, name="Test", lifetime_value_paise=1_000_000),
        ]
    )
    session.commit()
    session.close()
    return mid, cid


def _cleanup_case(case_id: str) -> None:
    session = SessionLocal()
    case = session.get(RecoveryCase, case_id)
    if case:
        from db.models import (
            AgentDecision,
            AuditLog,
            RecoveryAction,
            RecoveryOutcome,
        )

        for m in (AgentDecision, AuditLog, RecoveryOutcome, RecoveryAction):
            session.query(m).filter_by(case_id=case_id).delete()
        session.delete(case)
    session.commit()
    session.close()


def _cleanup_merchant_customer(mid: str, cid: str) -> None:
    from db.models import (
        CustomerRecoveryProfile,
        Experiment,
        ExperimentArm,
        Payment,
        RecoveryMemory,
    )

    session = SessionLocal()
    session.query(RecoveryMemory).filter_by(customer_id=cid).delete()
    session.query(Payment).filter_by(customer_id=cid).delete()
    profile = session.query(CustomerRecoveryProfile).filter_by(customer_id=cid).first()
    if profile:
        session.delete(profile)
    for exp in session.query(Experiment).filter_by(merchant_id=mid).all():
        session.query(ExperimentArm).filter_by(experiment_id=exp.id).delete()
        session.delete(exp)
    c = session.get(Customer, cid)
    if c:
        session.delete(c)
    m = session.get(Merchant, mid)
    if m:
        session.delete(m)
    session.commit()
    session.close()


# ---------------------------------------------------------------------------
# Standardized error shape
# ---------------------------------------------------------------------------


def test_error_shape_400():
    r = client.post(
        "/api/events/ingest",
        json={
            "event_id": "e",
            "event_type": "bogus.type",
            "merchant_id": "m",
            "customer_id": "c",
            "amount_paise": 100,
        },
    )
    assert r.status_code == 400
    body = r.json()
    assert "error" in body and "code" in body["error"] and "message" in body["error"]


def test_error_shape_404():
    r = client.get("/api/recovery/cases/does-not-exist")
    assert r.status_code == 404
    body = r.json()
    assert "error" in body and "code" in body["error"]


# ---------------------------------------------------------------------------
# End-to-end pipeline
# ---------------------------------------------------------------------------


def test_end_to_end_pipeline():
    mid, cid = _make_merchant_customer()
    event_id = f"evt_{uuid.uuid4().hex[:8]}"
    case_id = None
    try:
        # 1. Ingest payment.failed -> case + risk
        r = client.post(
            "/api/events/ingest",
            json={
                "event_id": event_id,
                "event_type": "payment.failed",
                "merchant_id": mid,
                "customer_id": cid,
                "amount_paise": 250_000,
                "payment_method": "upi",
                "failure_code": "INSUFFICIENT_FUNDS",
            },
        )
        assert r.status_code == 200
        case_id = r.json()["recovery_case_id"]
        assert case_id is not None

        # 2. Decision engine writes a decision + audit
        model = RecoveryModel.load("ml/artifacts/recovery_model.joblib")
        events = SyntheticDataGenerator(seed=42).generate(20).events
        feats = _features(events)
        session = SessionLocal()
        case = session.get(RecoveryCase, case_id)
        DecisionEngine(model).decide(case, feats, current_hour=14)
        session.close()

        # 3. Simulation runs eagerly
        from agents.tasks import run_simulation

        sim = run_simulation.apply(args=[100, 42, 14]).get()
        assert sim["baseline"]["total_events"] == 100
        assert isinstance(sim["incremental_paise"], int)

        # 4. Analytics reflects at-risk from the ingested case
        overview = client.get("/api/analytics/overview").json()
        assert isinstance(overview["revenue_at_risk_paise"], int)
        assert overview["revenue_at_risk_paise"] >= 250_000

        # 5. Drill-down timeline has a decision entry (AC-08)
        detail = client.get(f"/api/recovery/cases/{case_id}").json()
        assert len(detail["timeline"]) >= 1
        assert any(e["type"] == "decision" for e in detail["timeline"])
    finally:
        if case_id:
            _cleanup_case(case_id)
        _cleanup_merchant_customer(mid, cid)
