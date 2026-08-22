"""Recovery case read endpoints: queue + detail with decision timeline."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.schemas import CaseDetail, CaseSummary, PaginatedCases, TimelineEntry
from db.database import get_db
from db.models import AgentDecision, AuditLog, RecoveryCase

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
