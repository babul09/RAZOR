"""Unit tests for the Phase 4 diagnosis agent, explanation agent, and Celery tasks."""
from __future__ import annotations

import inspect
import uuid
from types import SimpleNamespace

import pytest

from agents.diagnosis_agent import Diagnosis, DiagnosisAgent
from config import settings
from db.database import SessionLocal
from db.models import (
    AgentDecision,
    AuditLog,
    Customer,
    Merchant,
    RecoveryCase,
    RecoveryCaseStatus,
)
from engine.decision_engine import Decision


class FakeClient:
    """Minimal mock of a Gemini client (generate_content -> .text)."""

    def __init__(self, text: str):
        self._text = text

    def generate_content(self, prompt: str):
        return SimpleNamespace(text=self._text)


def _case(**kw):
    defaults = dict(
        failure_code="INSUFFICIENT_FUNDS",
        amount_at_risk_paise=500_000,
        failure_reason=None,
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _profile(prob: float = 0.6):
    return SimpleNamespace(overall_recovery_probability=prob)


def _customer(start: int = 19, end: int = 22):
    return SimpleNamespace(typical_payment_hour_start=start, typical_payment_hour_end=end)


def _decision(strategy: str = "RETRY", reasoning: str = "best EV", net: int = 300_000):
    return Decision(
        case_id="c1",
        candidate_strategy=strategy,
        selected_strategy=strategy,
        expected_net_recovery_paise=net,
        reasoning=reasoning,
        policy_check_passed=True,
        recommended_at=None,
        status="STRATEGY_SELECTED",
    )


# ---------------------------------------------------------------------------
# Diagnosis agent — Wave 1
# ---------------------------------------------------------------------------


def test_rule_based_fallback_offline(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")  # force offline
    agent = DiagnosisAgent()  # no key, no mock
    d = agent.diagnose(_case(), customer=_customer(), profile=_profile(0.6))
    assert isinstance(d, Diagnosis)
    assert 0.0 <= d.confidence <= 1.0
    assert d.diagnosis
    assert d.recommended_timing
    assert d.reason
    assert isinstance(d.avoid_discount, bool)


def test_llm_path_with_mock():
    text = (
        '{"diagnosis":"Low balance","confidence":0.8,"recommended_timing":"Evening",'
        '"reason":"insufficient funds","avoid_discount":false}'
    )
    agent = DiagnosisAgent(client=FakeClient(text))
    d = agent.diagnose(_case())
    assert d.diagnosis == "Low balance"
    assert d.confidence == 0.8
    assert d.recommended_timing == "Evening"
    assert d.avoid_discount is False


def test_malformed_llm_falls_back():
    agent = DiagnosisAgent(client=FakeClient("this is not json at all"))
    d = agent.diagnose(_case(), customer=_customer(), profile=_profile())
    assert isinstance(d, Diagnosis)
    assert d.diagnosis  # rule-based fallback is non-empty


def test_llm_json_in_code_fence_parsed():
    text = "```json\n{\"diagnosis\":\"X\",\"confidence\":0.5,\"recommended_timing\":\"Any\",\"reason\":\"r\",\"avoid_discount\":true}\n```"
    agent = DiagnosisAgent(client=FakeClient(text))
    d = agent.diagnose(_case())
    assert d.diagnosis == "X"
    assert d.avoid_discount is True


def test_avoid_discount_flag(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")  # force offline
    agent = DiagnosisAgent()
    small = agent.diagnose(_case(amount_at_risk_paise=50_000))
    large = agent.diagnose(_case(amount_at_risk_paise=900_000))
    assert small.avoid_discount is True
    assert large.avoid_discount is False


def test_agent_never_executes_payment():
    from agents import diagnosis_agent as da

    src = inspect.getsource(da)
    assert "ActionExecutor" not in src
    assert "outcome_verifier" not in src
    assert "execute_payment" not in src


# ---------------------------------------------------------------------------
# Explanation agent — Wave 2
# ---------------------------------------------------------------------------


def test_explanation_template_fallback(monkeypatch):
    from agents.explanation_agent import ExplanationAgent

    monkeypatch.setattr(settings, "gemini_api_key", "")  # force offline
    agent = ExplanationAgent()  # no key, no mock
    d = agent.explain(_decision("RETRY"), _case())
    assert isinstance(d, str) and d
    assert "RETRY" in d


def test_explanation_gemini_path_with_mock():
    from agents.explanation_agent import ExplanationAgent

    agent = ExplanationAgent(client=FakeClient("Retry tonight, high chance."))
    d = agent.explain(_decision("RETRY"), _case())
    assert isinstance(d, str) and d
    assert "Retry tonight" in d


def test_explanation_mentions_strategy(monkeypatch):
    from agents.explanation_agent import ExplanationAgent

    monkeypatch.setattr(settings, "gemini_api_key", "")  # force offline
    agent = ExplanationAgent()
    d = agent.explain(_decision("WHATSAPP_REMINDER"), _case())
    assert "WHATSAPP_REMINDER" in d


# ---------------------------------------------------------------------------
# Celery tasks — Wave 2 (live DB, eager mode)
# ---------------------------------------------------------------------------


def _make_case_db(amount_paise: int) -> tuple[RecoveryCase, str, str]:
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
                status=RecoveryCaseStatus.NEW.value,
            ),
        ]
    )
    session.commit()
    case = session.get(RecoveryCase, case_id)
    session.close()
    return case, merchant_id, customer_id


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


def test_celery_tasks_registered():
    from agents.celery_app import celery_app
    import agents.tasks  # noqa: F401  # triggers task registration

    names = {t.name for t in celery_app.tasks.values()}
    assert "diagnose_case" in names
    assert "explain_decision" in names


def test_diagnose_case_task_eager():
    from agents.tasks import diagnose_case

    case, mid, cid = _make_case_db(100_000)
    try:
        result = diagnose_case.apply(args=[case.id]).get()
        assert result["ok"] is True
        assert result["diagnosis"]["diagnosis"]
        session = SessionLocal()
        logs = session.query(AuditLog).filter_by(case_id=case.id, event_type="DIAGNOSIS").count()
        session.close()
        assert logs >= 1
    finally:
        session = SessionLocal()
        _cleanup(session, case.id, mid, cid)
        session.close()


def test_explain_decision_task_eager():
    from agents.tasks import diagnose_case, explain_decision

    case, mid, cid = _make_case_db(100_000)
    try:
        diag = diagnose_case.apply(args=[case.id]).get()
        assert diag["ok"] is True
        result = explain_decision.apply(args=[case.id]).get()
        assert result["ok"] is True
        assert result["explanation"]
        session = SessionLocal()
        logs = session.query(AuditLog).filter_by(case_id=case.id, event_type="EXPLANATION").count()
        session.close()
        assert logs >= 1
    finally:
        session = SessionLocal()
        _cleanup(session, case.id, mid, cid)
        session.close()

