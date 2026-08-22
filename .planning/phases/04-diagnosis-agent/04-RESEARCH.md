# Phase 4: Diagnosis Agent (Gemini) — Research

**Researched:** 2026-08-22
**Domain:** LLM-assisted structured diagnosis with offline fallback and Celery async.
**Confidence:** HIGH

## Locked Decisions (user-confirmed)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Async model | **Celery + Redis now** | Redis running (PONG on :6379); celery 5.6.3 + redis 6.4.0 installed. |
| Gemini key | **Gated Gemini + mock tests** | No API key in `.env`; build gated client path, tests inject mock; rule-based fallback offline. |
| Explanation agent | **Include** | Roadmap Phase 4 item: `agents/explanation_agent.py`. |

## Environment (verified)

- Redis running on `localhost:6379` (`redis-cli ping` → PONG).
- `celery 5.6.3`, `redis 6.4.0`, `google-generativeai` SDK installed; `pip check` clean.
- `config.py` `gemini_api_key` is empty → Gemini path gated behind presence of key (or injected mock client).
- Phase 1-3 give `RecoveryCase`, `Customer`, `CustomerRecoveryProfile`, `AgentDecision`, `AuditLog` in PostgreSQL; `engine/` decision logic.

## Requirements

- **FR-04** Diagnosis Agent (LLM): input = payment data + customer profile + historical context; output = `{ diagnosis, confidence, recommended_timing, reason, avoid_discount }`; **LLM must not directly execute any payment action**.
- **AC-02** Diagnosis agent outputs structured JSON reasoning for any failure.
- **NFR-05** LLM is never in the critical path for money calculation or payment execution.
- Roadmap Phase 4: gemini-pro for diagnosis, gemini-flash for explanations; async non-blocking (Celery); fallback rule-based when LLM unavailable.

## Design

### `agents/diagnosis_agent.py` — `DiagnosisAgent.diagnose(case, ...)`
- Public `Diagnosis` dataclass with the FR-04 schema: `diagnosis`, `confidence`, `recommended_timing`, `reason`, `avoid_discount`.
- `DiagnosisAgent.__init__(client=None, model=None)`: builds a real Gemini client only when a key is present (or an injected mock); otherwise falls back to rule-based.
- `diagnose(case)`: builds prompt from payment/customer/profile/history; calls LLM; parses + validates structured JSON; on failure or no LLM → rule-based fallback. Never touches money or payment execution (NFR-05).
- Rule-based fallback: diagnosis from `failure_code`/category, confidence from `CustomerRecoveryProfile.overall_recovery_probability`, `recommended_timing` from `Customer.typical_payment_hour_*`, `avoid_discount` from segment/cost heuristics.

### `agents/explanation_agent.py` — `ExplanationAgent.explain(decision, diagnosis)`
- Generates a human-readable explanation string for the dashboard from a `Decision` + `Diagnosis`.
- Gemini-flash path (gated) with a deterministic template fallback so output is stable offline.

### `agents/celery_app.py` + `agents/tasks.py`
- Celery app bound to `config.settings.redis_url`; tasks `diagnose_case(case_id)` and `explain_decision(case_id)`.
- Celery workers run in a separate process; tests assert task registration + direct `run()` (eager) without needing a broker, plus one integration check against the running Redis.

## Risk / mitigation
- **No Gemini key** → gate client behind key/mock; tests use an injected mock client and assert schema parsing; rule-based fallback guarantees AC-02 offline.
- **Celery broker dependency** → tests use `task.apply()` (eager, no broker) for logic; a single opt-in integration test pings the running Redis. Document `celery -A agents.celery_app worker` for real async.
- **LLM output not JSON** → robust JSON extraction + schema validation; fallback on parse error (never crashes the recovery path).
- **Money/payment safety** → diagnosis writes only; no payment action ever invoked from the agent.
