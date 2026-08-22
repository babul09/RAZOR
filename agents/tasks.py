"""Celery tasks: asynchronous diagnosis and explanation (Phase 4).

Tasks write informational rows only (AgentDecision / AuditLog). They never
execute a payment and never perform money arithmetic (NFR-05).
"""
from __future__ import annotations

from agents.celery_app import celery_app
from agents.diagnosis_agent import DiagnosisAgent
from agents.explanation_agent import ExplanationAgent
from db.database import SessionLocal
from db.models import AgentDecision, AuditLog, Customer, CustomerRecoveryProfile, RecoveryCase


@celery_app.task(name="diagnose_case")
def diagnose_case(case_id: str) -> dict:
    """Asynchronously diagnose a recovery case and record the result."""
    agent = DiagnosisAgent()
    session = SessionLocal()
    try:
        case = session.get(RecoveryCase, case_id)
        if case is None:
            return {"ok": False, "error": "case not found"}
        customer = session.get(Customer, case.customer_id) if case.customer_id else None
        profile = (
            session.query(CustomerRecoveryProfile)
            .filter_by(customer_id=case.customer_id)
            .first()
        )
        diagnosis = agent.diagnose(case, customer=customer, profile=profile)
        payload = diagnosis.to_dict()
        session.add(
            AgentDecision(
                case_id=case_id,
                input_json={"diagnosis": payload},
                selected_strategy="DIAGNOSIS",
                reasoning=payload["reason"],
                policy_check_passed=None,
            )
        )
        session.add(
            AuditLog(
                case_id=case_id,
                event_type="DIAGNOSIS",
                details_json=payload,
            )
        )
        session.commit()
        return {"ok": True, "case_id": case_id, "diagnosis": payload}
    finally:
        session.close()


def dispatch_diagnosis(case_id: str) -> str:
    """Dispatch async diagnosis via Celery, falling back to an inline (eager) run
    when no broker/worker is reachable, so diagnosis always completes."""
    try:
        async_result = diagnose_case.delay(case_id)
        return async_result.id
    except Exception:
        diagnose_case.run(case_id)
        return "inline"


@celery_app.task(name="explain_decision")
def explain_decision(case_id: str) -> dict:
    """Asynchronously produce a human-readable explanation for a case's decision."""
    agent = ExplanationAgent()
    session = SessionLocal()
    try:
        case = session.get(RecoveryCase, case_id)
        if case is None:
            return {"ok": False, "error": "case not found"}
        decision_row = (
            session.query(AgentDecision)
            .filter_by(case_id=case_id)
            .order_by(AgentDecision.created_at.desc())
            .first()
        )
        if decision_row is None:
            return {"ok": False, "error": "no decision found"}
        diagnosis_text = "no diagnosis"
        if decision_row.input_json and "diagnosis" in decision_row.input_json:
            diagnosis_text = decision_row.input_json["diagnosis"].get("diagnosis", "no diagnosis")
        explanation = agent.explain(decision_row, SimpleDiagnosis(diagnosis_text))
        session.add(
            AuditLog(
                case_id=case_id,
                event_type="EXPLANATION",
                details_json={"explanation": explanation},
            )
        )
        session.commit()
        return {"ok": True, "case_id": case_id, "explanation": explanation}
    finally:
        session.close()


class SimpleDiagnosis:
    """Minimal diagnosis view for the explanation template."""

    def __init__(self, diagnosis: str):
        self.diagnosis = diagnosis


@celery_app.task(name="update_profile")
def update_profile(customer_id: str) -> dict:
    """Asynchronously recompute a customer's recovery profile from memory (FR-11)."""
    from engine.recovery_memory import update_profile as _update_profile

    session = SessionLocal()
    try:
        profile = _update_profile(session, customer_id)
        if profile is None:
            return {"ok": False, "error": "customer not found"}
        return {
            "ok": True,
            "customer_id": customer_id,
            "overall_recovery_probability": profile.overall_recovery_probability,
        }
    finally:
        session.close()


@celery_app.task(name="run_simulation")
def run_simulation(n_events: int, seed: int = 42, hour: int = 14) -> dict:
    """Run the baseline + RAZOR simulators and return the comparison dict (FR-13)."""
    from dataclasses import asdict

    from simulation.baseline_simulator import BaselineSimulator
    from simulation.generator import SyntheticDataGenerator
    from simulation.razor_simulator import RazorSimulator

    dataset = SyntheticDataGenerator(seed=seed).generate(n_events)
    baseline = BaselineSimulator(seed=seed).run(dataset.events)
    razor = RazorSimulator(seed=seed).run(dataset.events, current_hour=hour)
    return {
        "baseline": asdict(baseline),
        "razor": asdict(razor),
        "incremental_paise": razor.net_recovered_paise - baseline.net_recovered_paise,
    }
