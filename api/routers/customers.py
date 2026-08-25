"""Customer search endpoints for the operator console."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.schemas import CustomerSearchHit
from db.database import get_db
from db.models import Customer, RecoveryCase, RecoveryOutcome

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("", response_model=list[CustomerSearchHit])
def search_customers(q: str = "", db: Session = Depends(get_db)) -> list[CustomerSearchHit]:
    """Search customers by id, name, email, or phone; include their recovery stats."""
    query = db.query(Customer)
    if q and q.strip():
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Customer.id.ilike(like),
                Customer.name.ilike(like),
                Customer.email.ilike(like),
                Customer.phone.ilike(like),
            )
        )
    customers = query.order_by(Customer.lifetime_value_paise.desc()).limit(50).all()
    if not customers:
        return []

    ids = [c.id for c in customers]

    case_stats = {
        row[0]: {"total_cases": int(row[1]), "at_risk_paise": int(row[2])}
        for row in db.query(
            RecoveryCase.customer_id,
            func.count(RecoveryCase.id),
            func.coalesce(func.sum(RecoveryCase.amount_at_risk_paise), 0),
        )
        .filter(RecoveryCase.customer_id.in_(ids))
        .group_by(RecoveryCase.customer_id)
        .all()
    }
    recovered_stats = {
        row[0]: int(row[1])
        for row in db.query(
            RecoveryCase.customer_id,
            func.coalesce(func.sum(RecoveryOutcome.revenue_recovered_paise), 0),
        )
        .join(RecoveryOutcome, RecoveryOutcome.case_id == RecoveryCase.id)
        .filter(RecoveryCase.customer_id.in_(ids))
        .group_by(RecoveryCase.customer_id)
        .all()
    }
    case_rows = (
        db.query(RecoveryCase)
        .filter(RecoveryCase.customer_id.in_(ids))
        .order_by(RecoveryCase.priority.desc(), RecoveryCase.created_at.desc())
        .limit(500)
        .all()
    )
    by_customer: dict[str, list] = {}
    for case in case_rows:
        by_customer.setdefault(case.customer_id, []).append(
            {
                "id": case.id,
                "amount_at_risk_paise": case.amount_at_risk_paise,
                "failure_code": case.failure_code,
                "status": case.status,
            }
        )

    return [
        CustomerSearchHit(
            id=c.id,
            name=c.name,
            email=c.email,
            phone=c.phone,
            lifetime_value_paise=c.lifetime_value_paise,
            segment=c.customer_segment,
            total_cases=case_stats.get(c.id, {}).get("total_cases", 0),
            at_risk_paise=case_stats.get(c.id, {}).get("at_risk_paise", 0),
            recovered_paise=recovered_stats.get(c.id, 0),
            cases=by_customer.get(c.id, []),
        )
        for c in customers
    ]
