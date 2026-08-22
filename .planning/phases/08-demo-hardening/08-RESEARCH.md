# Phase 8: Demo Hardening & Integration Tests — Research

**Researched:** 2026-08-22
**Domain:** End-to-end integration validation of the full RAZOR pipeline + demo-flow proof.
**Confidence:** HIGH.

## Locked Decisions (user-confirmed)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Demo validation | **pytest-based** | A pytest test asserts all 10 killer-demo steps end-to-end. |
| Integration test | **Live DB + Redis** | Ingest → decision → simulation → API, runs when local services are up. |
| Error handling | **Standardize error shape** | Consistent structured error body across all API routes. |
| UI states | **Add loading/empty states** | Ensure every dashboard section handles loading and empty data. |

## Environment (verified)

- PostgreSQL + Redis running locally; Celery app/tasks present.
- Full stack from Phases 1-7: generator/simulators, ML model, decision/policy/state engine, agents, FastAPI backend (SSE + CORS), Next.js dashboard.
- Backend suite: 65 tests pass. Dashboard builds.
- Known gaps to harden: unhandled route errors not structured consistently; some UI sections lack explicit empty/loading states.

## Requirements

- **FR-13/FR-14** hero moment: simulation comparison + dashboard results.
- **AC-01** simulation runs end-to-end and produces ₹ recovered > baseline.
- **AC-04** WAIT selection; **AC-05** policy blocks discount; **AC-06** drill-down; **AC-08** decisions logged.
- Demo flow (10 steps): generate events → ₹ at risk → diagnose → recoverable → strategy breakdown → simulation → ₹ recovered vs baseline → drill-down → policy block → learning loop.

## Design

### Integration + demo-flow tests (pytest, live DB+Redis)
- `tests/test_integration.py` — end-to-end: ingest events via API → recovery case created (risk) → decision engine picks strategy → simulation run (Celery) returns comparison → analytics API reflects data → drill-down timeline has decision/audit entries. Requires live DB (and Redis for the simulation task, run eagerly or with worker).
- `tests/test_demo_flow.py` — a single test walking the 10 demo steps, asserting each (Step 1 generate 10k; Step 2 at-risk; Step 3 diagnosis; Step 4 recoverable; Step 5 strategy breakdown; Step 6 simulation runs; Step 7 recovered vs baseline; Step 8 drill-down; Step 9 policy block; Step 10 learning loop/profile update). Marked to require DB; simulation via eager task to avoid needing a live worker.
- Use seeded/cleanup fixtures so tests are repeatable.

### Structured error handling
- `api/errors.py` — a standard error body `{ "error": { "code": str, "message": str } }` and helpers; register a FastAPI exception handler for `HTTPException` and a generic `Exception` handler (structured 500), so every route returns a consistent shape. Update existing `raise HTTPException(...)` call sites to the helper.

### UI loading/empty states
- Ensure every dashboard section shows a loading state while fetching and an empty state when no data: Overview, Live Queue, Agent Activity, Strategy Performance, Simulation (idle/loading/error), Drill-down.

## Risk / mitigation
- **Live services required** → integration tests run when DB/Redis up; use eager simulation to avoid a live Celery worker.
- **10-step flow brittleness** → assert step invariants (metrics > 0, timeline populated, policy block present) rather than exact demo numbers.
- **Error handler regressions** → keep existing 4xx semantics; only wrap the response shape.
- **UI** → build passes after adding states.
