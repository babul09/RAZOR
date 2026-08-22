"""10-step killer-demo flow validation (live DB, eager simulation)."""
from __future__ import annotations

import uuid

import pytest

from agents.diagnosis_agent import DiagnosisAgent
from db.database import SessionLocal
from db.models import (
    AgentDecision,
    AuditLog,
    Customer,
    CustomerRecoveryProfile,
    Merchant,
    RecoveryCase,
    RecoveryCaseStatus,
)
from engine.decision_engine import DecisionEngine
from engine.policy_engine import MerchantPolicy, PolicyEngine
from engine.recovery_memory import record_outcome, update_profile
from ml.recovery_model import RecoveryModel
from ml.training import FEATURE_COLUMNS, build_training_frame
from simulation.generator import SyntheticDataGenerator


def _features(events):
    row = build_training_frame(events, seed=42).iloc[0]
    return {k: row[k] for k in FEATURE_COLUMNS if k != "candidate_strategy"}


def _make_case(amount_paise: int) -> tuple[RecoveryCase, str, str]:
    mid = f"m_{uuid.uuid4().hex[:8]}"
    cid = f"c_{uuid.uuid4().hex[:8]}"
    case_id = f"case_{uuid.uuid4().hex[:8]}"
    session = SessionLocal()
    session.add_all(
        [
            Merchant(id=mid, name="Test"),
            Customer(id=cid, merchant_id=mid, name="Test", lifetime_value_paise=1_000_000),
            RecoveryCase(
                id=case_id,
                merchant_id=mid,
                customer_id=cid,
                amount_at_risk_paise=amount_paise,
                failure_code="INSUFFICIENT_FUNDS",
                status=RecoveryCaseStatus.NEW.value,
            ),
        ]
    )
    session.commit()
    case = session.get(RecoveryCase, case_id)
    session.close()
    return case, mid, cid


def _cleanup_case(session, case_id: str) -> None:
    from db.models import RecoveryAction, RecoveryOutcome

    for m in (AgentDecision, AuditLog, RecoveryOutcome, RecoveryAction):
        session.query(m).filter_by(case_id=case_id).delete()
    case = session.get(RecoveryCase, case_id)
    if case:
        session.delete(case)
    session.commit()


def _cleanup_mc(session, mid: str, cid: str) -> None:
    from db.models import Payment, RecoveryMemory

    session.query(RecoveryMemory).filter_by(customer_id=cid).delete()
    session.query(Payment).filter_by(customer_id=cid).delete()
    profile = session.query(CustomerRecoveryProfile).filter_by(customer_id=cid).first()
    if profile:
        session.delete(profile)
    c = session.get(Customer, cid)
    if c:
        session.delete(c)
    m = session.get(Merchant, mid)
    if m:
        session.delete(m)
    session.commit()


def test_demo_flow_steps():
    session = SessionLocal()
    case_id = None
    mid = cid = None
    try:
        # Step 1: Generate events -> revenue at risk > 0.
        events = SyntheticDataGenerator(seed=42).generate(500).events
        at_risk = sum(e.transaction_amount_paise for e in events)
        assert at_risk > 0

        # Step 2/3: Diagnosis agent produces the 5-field schema.
        case, mid, cid = _make_case(at_risk // len(events))
        case_id = case.id
        diag = DiagnosisAgent().diagnose(
            case,
            customer=session.get(Customer, cid),
        )
        assert {
            "diagnosis",
            "confidence",
            "recommended_timing",
            "reason",
            "avoid_discount",
        } <= set(diag.to_dict())
        assert 0.0 <= diag.confidence <= 1.0

        # Step 4/5: Decision engine -> recoverable amount + strategy breakdown.
        model = RecoveryModel.load("ml/artifacts/recovery_model.joblib")
        engine = DecisionEngine(model)
        feats = _features(events)
        evaluated = engine.evaluate_strategies(feats, case.amount_at_risk_paise, 14)
        assert evaluated
        best = max(evaluated, key=lambda r: r.expected_net_paise)
        assert best.expected_net_paise > 0

        # Step 6: Simulation runs (eager) and Step 7: RAZOR > baseline (AC-01).
        from agents.tasks import run_simulation

        sim = run_simulation.apply(args=[500, 42, 14]).get()
        baseline_rec = sim["baseline"]["total_recovered_paise"]
        razor_rec = sim["razor"]["total_recovered_paise"]
        assert razor_rec >= baseline_rec
        assert isinstance(sim["incremental_paise"], int)

        # Step 8: Drill-down timeline (decision + audit entries, AC-08).
        decision = engine.decide(case, feats, current_hour=14)
        assert decision.selected_strategy
        ads = session.query(AgentDecision).filter_by(case_id=case.id).count()
        logs = session.query(AuditLog).filter_by(case_id=case.id).count()
        assert ads >= 1 and logs >= 1

        # Step 9: Policy blocks a discount exceeding max_discount_percent (AC-05).
        pe = PolicyEngine(MerchantPolicy(merchant_id="x", max_discount_percent=10))
        block = pe.check(
            type("D", (), {"selected_strategy": "DISCOUNT_OFFER"})(),
            500_000,
            discount_rate=0.25,
        )
        assert block.status == "BLOCK"

        # Step 10: Learning loop -> memory + profile update.
        record_outcome(session, cid, "IF", "RETRY", "RECOVERED", True, case.amount_at_risk_paise)
        profile = update_profile(session, cid)
        assert profile is not None
        assert profile.retry_attempts >= 1
        assert profile.overall_recovery_probability == pytest.approx(1.0)
    finally:
        if case_id:
            _cleanup_case(session, case_id)
        if mid and cid:
            _cleanup_mc(session, mid, cid)
        session.close()
