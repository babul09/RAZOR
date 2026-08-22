# Plan 04-01 Summary — Diagnosis Agent (schema, fallback, gated Gemini)

**Phase:** 04-diagnosis-agent · **Plan:** 01 · **Wave:** 1
**Status:** COMPLETE

## What was built

- **`agents/__init__.py`** — agent-layer marker with NFR-05 safety note.
- **`agents/diagnosis_agent.py`** — `Diagnosis` dataclass (FR-04 schema: `diagnosis`, `confidence`, `recommended_timing`, `reason`, `avoid_discount`) and `DiagnosisAgent`:
  - `__init__(client=None, model="gemini-pro")` builds a Gemini client only when `settings.gemini_api_key` is set or a mock is injected; never fails offline.
  - `diagnose(case, customer=None, profile=None)` — LLM path with robust JSON extraction (code-fence tolerant) + schema validation; on any failure or no client, deterministic rule-based fallback (AC-02).
  - Rule-based: diagnosis from `failure_code`, confidence from `CustomerRecoveryProfile.overall_recovery_probability` (clamped [0,1]), timing from customer typical hours, `avoid_discount` from low-value heuristic.
  - Never executes payment / money arithmetic (NFR-05).
- **`tests/test_diagnosis_agent.py`** — Wave 1 tests: offline fallback schema, mock LLM parse, malformed→fallback, code-fence JSON, `avoid_discount`, no-payment source check.

## Verification
- `python -m pytest tests/test_diagnosis_agent.py -q` → **12 passed** (incl. Wave 2 tests).
- Full suite → **41 passed**.

## Notes
- Gemini SDK + celery/redis installed; dependency health clean (`pip check`).
