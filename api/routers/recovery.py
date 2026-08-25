"""Recovery case read endpoints: queue + detail with decision timeline."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from agents.diagnosis_agent import DiagnosisAgent
from agents.explanation_agent import ExplanationAgent
from api.schemas import CaseDetail, CaseSummary, PaginatedCases, TimelineEntry
from db.database import get_db
from db.models import AgentDecision, AuditLog, Customer, CustomerRecoveryProfile, RecoveryCase

router = APIRouter(prefix="/api/recovery", tags=["recovery"])

def _summary(case: RecoveryCase) -> CaseSummary:
    return CaseSummary(
        id=case.id,
        customer_id=case.customer_id,
        amount_at_risk_paise=case.amount_at_risk_paise,
        failure_code=case.failure_code,
        status=case.status,
        priority=case.priority or 0,
        recovery_probability=case.recovery_probability,
        created_at=case.created_at,
    )


@router.get("/cases", response_model=PaginatedCases)
def list_cases(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    db: Session = Depends(get_db),
) -> PaginatedCases:
    page = max(page, 1)
    page_size = max(1, min(page_size, 100))
    query = db.query(RecoveryCase)
    if status:
        query = query.filter(RecoveryCase.status == status)
    total = query.count()
    rows = (
        query.order_by(RecoveryCase.priority.desc(), RecoveryCase.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedCases(
        items=[_summary(c) for c in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/cases/{case_id}", response_model=CaseDetail)
def get_case(case_id: str, db: Session = Depends(get_db)) -> CaseDetail:
    case = db.get(RecoveryCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="case not found")

    timeline: list[TimelineEntry] = []
    for ad in (
        db.query(AgentDecision)
        .filter(AgentDecision.case_id == case_id)
        .order_by(AgentDecision.created_at)
        .all()
    ):
        timeline.append(
            TimelineEntry(
                type="decision",
                event_type="AGENT_DECISION",
                detail={
                    "selected_strategy": ad.selected_strategy,
                    "reasoning": ad.reasoning,
                    "policy_check_passed": ad.policy_check_passed,
                },
                created_at=ad.created_at,
            )
        )
    for log in (
        db.query(AuditLog)
        .filter(AuditLog.case_id == case_id)
        .order_by(AuditLog.created_at)
        .all()
    ):
        timeline.append(
            TimelineEntry(
                type="audit",
                event_type=log.event_type,
                detail=log.details_json,
                created_at=log.created_at,
            )
        )

    return CaseDetail(
        **_summary(case).model_dump(),
        source_type=case.source_type,
        source_id=case.source_id,
        failure_reason=case.failure_reason,
        timeline=timeline,
    )


@router.get("/events")
def recovery_events(db: Session = Depends(get_db)) -> StreamingResponse:
    """SSE stream of the latest recovery cases (dashboard live queue)."""

    async def event_generator():
        from fastapi.concurrency import run_in_threadpool

        while True:
            def snapshot():
                rows = (
                    db.query(RecoveryCase)
                    .order_by(RecoveryCase.priority.desc(), RecoveryCase.created_at.desc())
                    .limit(50)
                    .all()
                )
                return [_summary(c).model_dump() for c in rows]

            try:
                items = await run_in_threadpool(snapshot)
                yield f"data: {json.dumps(items, default=str)}\n\n"
            except Exception:
                yield "event: error\ndata: {}\n\n"
            await asyncio.sleep(3)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


class _Decision:
    """Minimal decision view for the explanation agent."""

    def __init__(self, selected_strategy: str | None, reasoning: str):
        self.selected_strategy = selected_strategy
        self.reasoning = reasoning


class _Diagnosis:
    """Minimal diagnosis view for the explanation agent."""

    def __init__(self, diagnosis: str):
        self.diagnosis = diagnosis


@router.post("/cases/{case_id}/explain")
def explain_case(case_id: str, db: Session = Depends(get_db)) -> dict:
    """Ensure a diagnosis exists and produce (or refresh) a Gemini explanation.

    Uses Gemini-flash when configured, else a deterministic fallback. Persists
    the explanation as an EXPLANATION audit entry so the timeline keeps it.
    """
    case = db.get(RecoveryCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="case not found")

    customer = db.get(Customer, case.customer_id) if case.customer_id else None
    profile = (
        db.query(CustomerRecoveryProfile)
        .filter_by(customer_id=case.customer_id)
        .first()
    )

    # Ensure a diagnosis exists.
    diag_audit = (
        db.query(AuditLog)
        .filter_by(case_id=case_id, event_type="DIAGNOSIS")
        .order_by(AuditLog.created_at.desc())
        .first()
    )
    if diag_audit and diag_audit.details_json:
        diagnosis = dict(diag_audit.details_json)
    else:
        diagnosis = DiagnosisAgent().diagnose(case, customer=customer, profile=profile).to_dict()
        db.add(
            AuditLog(case_id=case_id, event_type="DIAGNOSIS", details_json=diagnosis)
        )
        db.commit()

    decision_row = (
        db.query(AgentDecision)
        .filter_by(case_id=case_id)
        .order_by(AgentDecision.created_at.desc())
        .first()
    )
    if decision_row is None:
        explanation = "This case has not been decided yet, so there is nothing to explain."
    else:
        explanation = ExplanationAgent().explain(
            _Decision(decision_row.selected_strategy, decision_row.reasoning or ""),
            _Diagnosis(diagnosis.get("diagnosis", "no diagnosis")),
        )

    db.add(
        AuditLog(case_id=case_id, event_type="EXPLANATION", details_json={"explanation": explanation})
    )
    db.commit()
    return {"diagnosis": diagnosis, "explanation": explanation}
