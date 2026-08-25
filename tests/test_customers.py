"""Minimal customer-search contract test."""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from api.main import app
from db.database import SessionLocal
from db.models import (
    Customer,
    Merchant,
    Payment,
    RecoveryCase,
    RecoveryCaseStatus,
    RecoveryOutcome,
)

client = TestClient(app)
MERCHANT = "merchant_001"


def test_search_customers_returns_stats_and_cases():
    session = SessionLocal()
    cid = f"c_{uuid.uuid4().hex[:8]}"
    eid = f"e_{uuid.uuid4().hex[:8]}"
    case_id = f"cs_{uuid.uuid4().hex[:8]}"
    name = f"SearchUser{uuid.uuid4().hex[:6]}"
    if not session.get(Merchant, MERCHANT):
        session.add(Merchant(id=MERCHANT, name="Demo"))
    session.merge(Customer(id=cid, merchant_id=MERCHANT, name=name, email=f"{cid}@x.com", lifetime_value_paise=2_000_000, customer_segment="A"))
    session.merge(Payment(id=eid, merchant_id=MERCHANT, customer_id=cid, amount_paise=100_000, status="FAILED", failure_code="INSUFFICIENT_FUNDS"))
    session.merge(RecoveryCase(id=case_id, merchant_id=MERCHANT, customer_id=cid, source_type="payment", source_id=eid, amount_at_risk_paise=100_000, failure_code="INSUFFICIENT_FUNDS", status=RecoveryCaseStatus.RECOVERED.value))
    session.add(RecoveryOutcome(case_id=case_id, revenue_recovered_paise=100_000, cost_of_recovery_paise=200, net_revenue_recovered_paise=99_800, recovery_method="RETRY"))
    session.commit()
    session.close()

    try:
        # Search by partial name.
        r = client.get("/api/customers", params={"q": name[:12]})
        assert r.status_code == 200
        hits = r.json()
        assert any(h["id"] == cid for h in hits)
        hit = next(h for h in hits if h["id"] == cid)
        assert hit["name"] == name
        assert hit["total_cases"] == 1
        assert hit["at_risk_paise"] == 100_000
        assert hit["recovered_paise"] == 100_000
        assert hit["cases"][0]["status"] == "RECOVERED"

        # Search by exact email.
        r = client.get("/api/customers", params={"q": f"{cid}@x.com"})
        assert any(h["id"] == cid for h in r.json())

        # Non-matching query returns empty.
        assert client.get("/api/customers", params={"q": "zzz-no-such-user"}).json() == []
    finally:
        session = SessionLocal()
        case = session.get(RecoveryCase, case_id)
        if case:
            session.query(RecoveryOutcome).filter_by(case_id=case.id).delete()
            session.delete(case)
        session.delete(session.get(Payment, eid))
        session.delete(session.get(Customer, cid))
        session.commit()
        session.close()
