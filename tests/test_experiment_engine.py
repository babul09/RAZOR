"""Tests for the Phase 6 experiment engine + experiments API."""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from api.main import app
from db.database import SessionLocal
from db.models import Experiment, ExperimentArm, Merchant
from engine.experiment_engine import ExperimentEngine

client = TestClient(app)
_engine = ExperimentEngine()

ARMS = [
    {"arm_name": "control", "traffic_percent": 40, "strategy": None},
    {"arm_name": "retry", "traffic_percent": 30, "strategy": "RETRY"},
    {"arm_name": "whatsapp", "traffic_percent": 30, "strategy": "WHATSAPP_REMINDER"},
]


@pytest.fixture(scope="module")
def merchant_id():
    mid = f"m_{uuid.uuid4().hex[:8]}"
    session = SessionLocal()
    session.add(Merchant(id=mid, name="Test"))
    session.commit()
    session.close()
    yield mid
    session = SessionLocal()
    for exp in session.query(Experiment).filter_by(merchant_id=mid).all():
        session.query(ExperimentArm).filter_by(experiment_id=exp.id).delete()
        session.delete(exp)
    m = session.get(Merchant, mid)
    if m:
        session.delete(m)
    session.commit()
    session.close()


def _cleanup_experiment(session, experiment_id: str) -> None:
    session.query(ExperimentArm).filter_by(experiment_id=experiment_id).delete()
    experiment = session.get(Experiment, experiment_id)
    if experiment:
        session.delete(experiment)
    session.commit()


# ---------------------------------------------------------------------------
# Experiment engine
# ---------------------------------------------------------------------------


def test_create_experiment_validates_traffic(merchant_id):
    session = SessionLocal()
    exp = None
    try:
        exp = _engine.create_experiment(session, "Test Exp", ARMS, merchant_id)
        assert exp.id
        assert len(exp.arms) == 3
        with pytest.raises(ValueError):
            _engine.create_experiment(
                session, "Bad", [{"arm_name": "a", "traffic_percent": 50, "strategy": None}], merchant_id
            )
    finally:
        if exp is not None:
            _cleanup_experiment(session, exp.id)
        session.close()


def test_allocate_deterministic():
    a1 = _engine.allocate(ARMS, "cust-1", seed=42)
    a2 = _engine.allocate(ARMS, "cust-1", seed=42)
    assert a1 == a2  # same key -> same arm
    # All allocation results come from the arm strategies.
    assert a1 in {None, "RETRY", "WHATSAPP_REMINDER"}


def test_record_arm_metric_and_recovery_rate(merchant_id):
    session = SessionLocal()
    exp_id = None
    try:
        exp = _engine.create_experiment(session, "Metric Exp", ARMS, merchant_id)
        exp_id = exp.id
        arm = exp.arms[1]  # retry arm
        _engine.record_arm_metric(session, arm.id, True, 100_000)
        _engine.record_arm_metric(session, arm.id, False, 0)
        arm = session.get(ExperimentArm, arm.id)
        assert arm.attempts == 2
        assert arm.recoveries == 1
        assert arm.revenue_recovered_paise == 100_000
        assert arm.recoveries / arm.attempts == pytest.approx(0.5)  # AC-07 rate
    finally:
        if exp_id:
            _cleanup_experiment(session, exp_id)
        session.close()


def test_compute_strategy_weights(merchant_id):
    session = SessionLocal()
    exp_id = None
    try:
        exp = _engine.create_experiment(
            session,
            "Weight Exp",
            [
                {"arm_name": "a", "traffic_percent": 50, "strategy": "RETRY"},
                {"arm_name": "b", "traffic_percent": 50, "strategy": "WHATSAPP_REMINDER"},
            ],
            merchant_id,
        )
        exp_id = exp.id
        arm_a, arm_b = exp.arms
        _engine.record_arm_metric(session, arm_a.id, True, 100_000)  # 100%
        _engine.record_arm_metric(session, arm_a.id, True, 100_000)
        _engine.record_arm_metric(session, arm_b.id, True, 100_000)  # 50%
        _engine.record_arm_metric(session, arm_b.id, False, 0)
        weights = _engine.compute_strategy_weights(session)
        assert weights["RETRY"] == pytest.approx(1.0)  # best
        assert weights["WHATSAPP_REMINDER"] == pytest.approx(0.5)
        assert all(w > 0 for w in weights.values())
    finally:
        if exp_id:
            _cleanup_experiment(session, exp_id)
        session.close()


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def test_create_experiment_api(merchant_id):
    r = client.post(
        "/api/experiments",
        json={
            "name": "API Exp",
            "merchant_id": merchant_id,
            "arms": [{"arm_name": "c", "traffic_percent": 100, "strategy": "RETRY"}],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "API Exp"
    assert len(body["arms"]) == 1
    session = SessionLocal()
    _cleanup_experiment(session, body["id"])
    session.close()


def test_create_experiment_api_bad_traffic(merchant_id):
    r = client.post(
        "/api/experiments",
        json={
            "name": "Bad",
            "merchant_id": merchant_id,
            "arms": [{"arm_name": "c", "traffic_percent": 50, "strategy": "RETRY"}],
        },
    )
    assert r.status_code == 400


def test_weights_endpoint():
    r = client.get("/api/experiments/weights")
    assert r.status_code == 200
    assert isinstance(r.json(), dict)
