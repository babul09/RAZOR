# Plan 08-01 Summary — Structured Errors + E2E Integration Test

**Phase:** 08-demo-hardening · **Plan:** 01 · **Wave:** 1
**Status:** COMPLETE

## What was built

- **`api/errors.py`** — standardized error body `{"error": {"code", "message"}}`; `http_error(...)` helper + `register_exception_handlers(app)` (HTTPException re-shape + generic structured 500, no internals leaked).
- **`api/main.py`** — registers exception handlers.
- **`api/routers/{events,simulation,experiments}.py`** — 400s now use the standard shape (unsupported event_type, bad n_events, invalid experiment).
- **`tests/test_integration.py`** — error-shape tests (400/404) + `test_end_to_end_pipeline`: ingest payment.failed → case+risk → DecisionEngine.decide writes decision+audit (AC-08) → `run_simulation` eager → analytics reflects at-risk → drill-down timeline has decision entry. Live DB, eager simulation, full cleanup.

## Verification
- `python -m pytest tests/test_integration.py -q` → **3 passed**.
- Full suite → **69 passed**.

## Notes
- Fixed cleanup FK issues (deleting a case nulls `agent_decisions.case_id`; deleting a customer nulls `payments.customer_id`) — cleaned dependents first.
- Refactored `DecisionEngine._persist` to re-fetch the case by id (more robust than merging the passed ORM object).
