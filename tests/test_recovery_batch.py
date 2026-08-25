"""Tests for breadth + measured-real-batch recovery execution.

Covers: all four revenue-at-risk event types are executed into
RecoveryAction/RecoveryOutcome, policy stays a hard gate, and the analytics
overview incremental headline traces to executed outcomes (not simulation).
"""
from __future__ import annotations

import uuid

import pytest

from engine.policy_engine import MerchantPolicy
from engine.recovery_batch import RecoveryBatchExecutor
from ml.recovery_model import RecoveryModel
from db.database import SessionLocal
from db.models import (
    Customer,
    Merchant,
    Payment,
    RecoveryCase,
    RecoveryCaseStatus,
    RecoveryOutcome,
    RecoveryAction,
    RecoveryMemory,
    AgentDecision,
    AuditLog,
)

SOURCE_TYPES = ("payment", "checkout", "subscription", "invoice")

_EXECUTABLE = (
    RecoveryCaseStatus.NEW,
    RecoveryCaseStatus.STRATEGY_SELECTED,
    RecoveryCaseStatus.FAILED,
)


@pytest.fixture(scope="module", autouse=True)
def _sweep_leftover_cases():
    """Remove transient in-progress cases left by aborted runs so each test
    only processes the cases it seeds (keeps batch runs fast)."""
    session = SessionLocal()
    ids = [
        r[0]
        for r in session.query(RecoveryCase.id)
        .filter(RecoveryCase.status.in_([s.value for s in _EXECUTABLE]))
        .all()
    ]
    for m in (RecoveryOutcome, RecoveryAction, AgentDecision, AuditLog):
        session.query(m).filter(m.case_id.in_(ids)).delete(synchronize_session=False)
    if ids:
        session.query(RecoveryCase).filter(RecoveryCase.id.in_(ids)).delete(
            synchronize_session=False
        )
    session.commit()
    session.close()
    yield


def _seed_case(source_type: str, amount_paise: int = 100_000) -> dict:
    mid = f"m_{uuid.uuid4().hex[:8]}"
    cid = f"c_{uuid.uuid4().hex[:8]}"
    event_id = f"evt_{uuid.uuid4().hex[:8]}"
    case_id = f"case_{uuid.uuid4().hex[:8]}"
    session = SessionLocal()
    session.add_all(
        [
            Merchant(id=mid, name="Test"),
            Customer(
                id=cid,
                merchant_id=mid,
                name="Test",
                lifetime_value_paise=1_000_000,
                customer_segment="C",
            ),
            Payment(
                id=event_id,
                merchant_id=mid,
                customer_id=cid,
                amount_paise=amount_paise,
                status="FAILED",
                failure_code="INSUFFICIENT_FUNDS",
            ),
            RecoveryCase(
                id=case_id,
                merchant_id=mid,
                customer_id=cid,
                source_type=source_type,
                source_id=event_id,
                amount_at_risk_paise=amount_paise,
                failure_code="INSUFFICIENT_FUNDS",
                status=RecoveryCaseStatus.NEW.value,
                priority=50,
            ),
        ]
    )
    session.commit()
    session.close()
    return {"mid": mid, "cid": cid, "event_id": event_id, "case_id": case_id}


def _cleanup(refs: dict) -> None:
    session = SessionLocal()
    case = session.get(RecoveryCase, refs["case_id"])
    if case:
        for m in (AgentDecision, AuditLog, RecoveryOutcome, RecoveryAction):
            session.query(m).filter_by(case_id=case.id).delete()
        session.delete(case)
    payment = session.get(Payment, refs["event_id"])
    if payment:
        session.delete(payment)
    session.query(RecoveryMemory).filter_by(customer_id=refs["cid"]).delete()
    c = session.get(Customer, refs["cid"])
    if c:
        session.delete(c)
    m = session.get(Merchant, refs["mid"])
    if m:
        session.delete(m)
    session.commit()
    session.close()


def _policy() -> MerchantPolicy:
    return MerchantPolicy(
        merchant_id="merchant_001",
        max_automated_amount_paise=500_000,
        require_human_approval_above_paise=10_000_000,
        wait_window_start_hour=None,  # never WAIT
    )


def test_batch_executes_all_four_event_types():
    refs = [_seed_case(s) for s in SOURCE_TYPES]
    try:
        model = RecoveryModel.load("ml/artifacts/recovery_model.joblib")
        result = RecoveryBatchExecutor(model, _policy(), current_hour=14).run(limit=100)

        assert result.executed == 4
        assert result.processed_cases == 4
        assert set(m.source_type for m in result.per_source) == set(SOURCE_TYPES)
        assert all(m.attempts == 1 for m in result.per_source)

        # Every source type produced an executed outcome in the DB.
        session = SessionLocal()
        try:
            for ref in refs:
                case = session.get(RecoveryCase, ref["case_id"])
                assert case.status in (
                    RecoveryCaseStatus.RECOVERED.value,
                    RecoveryCaseStatus.FAILED.value,
                )
                assert session.query(RecoveryAction).filter_by(case_id=case.id).count() == 1
                assert session.query(RecoveryOutcome).filter_by(case_id=case.id).count() == 1
        finally:
            session.close()

        assert result.recovered_paise >= 0
        assert result.incremental_paise == result.recovered_paise - int(
            result.at_risk_paise * 0.15
        )
    finally:
        for ref in refs:
            _cleanup(ref)


def test_policy_hard_gate_blocks_high_value_case():
    # Amount above max_automated_amount_paise -> APPROVAL_REQUIRED, no execution.
    ref = _seed_case("payment", amount_paise=5_000_000)
    try:
        policy = MerchantPolicy(
            merchant_id="merchant_001",
            max_automated_amount_paise=100_000,
            require_human_approval_above_paise=100_000,
            wait_window_start_hour=None,
        )
        model = RecoveryModel.load("ml/artifacts/recovery_model.joblib")
        result = RecoveryBatchExecutor(model, policy, current_hour=14).run(limit=100)

        assert result.executed == 0
        session = SessionLocal()
        try:
            case = session.get(RecoveryCase, ref["case_id"])
            assert session.query(RecoveryOutcome).filter_by(case_id=case.id).count() == 0
            assert session.query(RecoveryAction).filter_by(case_id=case.id).count() == 0
            assert case.status == RecoveryCaseStatus.AWAITING_APPROVAL.value
        finally:
            session.close()
    finally:
        _cleanup(ref)


def test_overview_incremental_traces_to_executed_outcomes():
    from api.routers.analytics import _cache, OVERVIEW_KEY, invalidate_overview_cache
    from fastapi.testclient import TestClient
    from api.main import app

    ref = _seed_case("payment", amount_paise=100_000)
    try:
        invalidate_overview_cache()
        client = TestClient(app)
        before = client.get("/api/analytics/overview").json()
        before_recovered = before["recovered_paise"]

        model = RecoveryModel.load("ml/artifacts/recovery_model.joblib")
        RecoveryBatchExecutor(model, _policy(), current_hour=14).run(limit=100)
        invalidate_overview_cache()

        after = client.get("/api/analytics/overview").json()
        # Executing recovery adds measured money from executed outcomes.
        assert after["recovered_paise"] >= before_recovered
        assert isinstance(after["incremental_paise"], int)
        assert after["incremental_paise"] == after["recovered_paise"] - int(
            after["executed_at_risk_paise"] * 0.15
        )

        # The seed case produced an executed outcome in the DB.
        session = SessionLocal()
        try:
            case = session.get(RecoveryCase, ref["case_id"])
            assert session.query(RecoveryOutcome).filter_by(case_id=case.id).count() == 1
        finally:
            session.close()
    finally:
        _cache.delete(OVERVIEW_KEY)
        _cleanup(ref)
