"""DB-backed unit tests for the Phase 3 policy engine and outcome verifier."""
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
    RecoveryMemory,
    RecoveryOutcome,
)
from engine.decision_engine import Decision
from engine.outcome_verifier import ActionExecutor, OutcomeVerifier
from engine.policy_engine import MerchantPolicy, PolicyEngine, load_policy_yaml

POLICY_PATH = "engine/policies/merchant_001.yaml"


def _decision(strategy: str) -> Decision:
    return Decision(
        case_id="x",
        candidate_strategy=strategy,
        selected_strategy=strategy,
        expected_net_recovery_paise=0,
        reasoning="test",
        policy_check_passed=None,
        recommended_at=None,
        status="STRATEGY_SELECTED",
    )


# ---------------------------------------------------------------------------
# Policy engine
# ---------------------------------------------------------------------------


def test_load_policy_yaml():
    policy = load_policy_yaml(POLICY_PATH)
    assert policy.merchant_id == "merchant_001"
    assert policy.max_discount_percent == 10
    assert policy.wait_window == (19, 22)
    assert policy.allowed_channels == ["whatsapp", "email"]
    assert policy.max_discount_rate == 0.10


def test_load_policy_yaml_defaults(tmp_path):
    path = tmp_path / "minimal.yaml"
    path.write_text("merchant_id: m_x\n")
    policy = load_policy_yaml(path)
    assert policy.merchant_id == "m_x"
    assert policy.max_discount_percent == 10
    assert policy.wait_window == (19, 22)
    assert policy.allowed_channels == ["whatsapp", "email"]


def test_load_policy_yaml_missing_raises(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("foo: bar\n")
    with pytest.raises(ValueError):
        load_policy_yaml(path)


def test_discount_block_ac05():
    pe = PolicyEngine(MerchantPolicy(merchant_id="x", max_discount_percent=10))
    blocked = pe.check(_decision("DISCOUNT_OFFER"), 500_000, discount_rate=0.25)
    assert blocked.status == "BLOCK"
    assert "max_discount_percent" in blocked.reason
    passed = pe.check(_decision("DISCOUNT_OFFER"), 500_000, discount_rate=0.10)
    assert passed.status == "PASS"


def test_high_amount_approval_required():
    pe = PolicyEngine(MerchantPolicy(merchant_id="x"))
    res = pe.check(_decision("RETRY"), 900_000)
    assert res.status == "APPROVAL_REQUIRED"


def test_channel_not_allowed_block():
    pe = PolicyEngine(MerchantPolicy(merchant_id="x", allowed_channels=["email"]))
    res = pe.check(_decision("WHATSAPP_REMINDER"), 10_000)
    assert res.status == "BLOCK"
    assert "channel" in res.reason


def test_contacts_limit_block():
    pe = PolicyEngine(MerchantPolicy(merchant_id="x", max_contacts_count=3))
    res = pe.check(_decision("RETRY"), 10_000, contacts_in_window=3)
    assert res.status == "BLOCK"
    assert "max_contacts_count" in res.reason


def test_wait_and_stop_pass_gate():
    pe = PolicyEngine(MerchantPolicy(merchant_id="x"))
    assert pe.check(_decision("WAIT"), 900_000).status == "PASS"
    assert pe.check(_decision("STOP"), 900_000).status == "PASS"


def test_stop_if_payment_succeeded_block():
    pe = PolicyEngine(MerchantPolicy(merchant_id="x", stop_if_payment_succeeds=True))
    res = pe.check(_decision("RETRY"), 10_000, payment_succeeded=True)
    assert res.status == "BLOCK"


# ---------------------------------------------------------------------------
# Outcome verifier (live DB)
# ---------------------------------------------------------------------------


def _make_case(amount_paise: int) -> tuple[RecoveryCase, str, str]:
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
                status=RecoveryCaseStatus.NEW.value,
            ),
        ]
    )
    session.commit()
    case = session.get(RecoveryCase, case_id)
    session.close()
    return case, merchant_id, customer_id


def _cleanup(session, case_id: str, merchant_id: str, customer_id: str) -> None:
    session.query(RecoveryOutcome).filter_by(case_id=case_id).delete()
    session.query(RecoveryMemory).filter_by(customer_id=customer_id).delete()
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


def test_outcome_verifier_records_outcome():
    case, merchant_id, customer_id = _make_case(100_000)
    try:
        verifier = OutcomeVerifier(ActionExecutor(seed=42))
        outcome = verifier.verify(case, "A", "RETRY", 100_000)
        assert outcome.recovery_method == "RETRY"
        assert (
            outcome.net_revenue_recovered_paise
            == outcome.revenue_recovered_paise - outcome.cost_of_recovery_paise
        )
        session = SessionLocal()
        status = session.get(RecoveryCase, case.id).status
        outcomes = session.query(RecoveryOutcome).filter_by(case_id=case.id).count()
        session.close()
        assert outcomes == 1
        assert status in (
            RecoveryCaseStatus.RECOVERED.value,
            RecoveryCaseStatus.FAILED.value,
        )
    finally:
        session = SessionLocal()
        _cleanup(session, case.id, merchant_id, customer_id)
        session.close()


# ---------------------------------------------------------------------------
# Demo CLI smoke test
# ---------------------------------------------------------------------------


def test_demo_cli_smoke(capsys):
    from scripts.demo_decision_engine import main

    before = set(r[0] for r in SessionLocal().query(RecoveryCase.id).all())
    code = main(["--limit", "1", "--hour", "10"])
    after = set(r[0] for r in SessionLocal().query(RecoveryCase.id).all())
    captured = capsys.readouterr().out
    assert code == 0
    assert "AC-05" in captured
    assert "AC-04" in captured
    # Clean up only cases created by this run (demo auto-creates from failed payments).
    new_cases = after - before
    if new_cases:
        session = SessionLocal()
        for cid in new_cases:
            session.query(AgentDecision).filter_by(case_id=cid).delete()
            session.query(AuditLog).filter_by(case_id=cid).delete()
            session.query(RecoveryOutcome).filter_by(case_id=cid).delete()
            case = session.get(RecoveryCase, cid)
            if case:
                session.delete(case)
        session.commit()
        session.close()
