# Plan 04-02 Summary — Explanation Agent + Celery Async Tasks

**Phase:** 04-diagnosis-agent · **Plan:** 02 · **Wave:** 2
**Status:** COMPLETE

## What was built

- **`agents/explanation_agent.py`** — `ExplanationAgent.explain(decision, diagnosis) -> str`: gated Gemini-flash path with a deterministic template fallback referencing the selected strategy and diagnosis. Read-only.
- **`agents/celery_app.py`** — Celery app `razor`, broker/backend `settings.redis_url`, `include=["agents.tasks"]` so the worker auto-loads tasks.
- **`agents/tasks.py`** — `diagnose_case(case_id)` and `explain_decision(case_id)` shared tasks: load case/profile via `SessionLocal`, run agents, write informational rows (`AgentDecision` / `AuditLog` event_type DIAGNOSIS/EXPLANATION). No payment execution (NFR-05).
- **`tests/test_diagnosis_agent.py`** — Wave 2 tests: explanation template fallback, mock Gemini path, mentions strategy, task registration, and DB-backed eager-mode task tests.

## Verification
- `python -m pytest tests/test_diagnosis_agent.py -q` → **12 passed**.
- Full suite → **41 passed**.
- Celery app loads; `diagnose_case`, `explain_decision` registered; broker `redis://localhost:6379/0`.

## Notes
- Worker entry: `celery -A agents.celery_app worker --loglevel=info`.
- Eager-mode tests (`task.apply()`) need no broker; Redis integration check confirms broker reachable.
