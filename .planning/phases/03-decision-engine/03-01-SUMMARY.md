# Plan 03-01 Summary — State Machine + Decision Engine + DB Logging

**Phase:** 03-decision-engine · **Plan:** 01 · **Wave:** 1
**Status:** COMPLETE

## What was built

Tracer slice proving the decide→log→state loop end-to-end against live PostgreSQL:

- **`engine/__init__.py`** — engine package marker.
- **`engine/state_machine.py`** — `RecoveryStateMachine` + `StateEvent`: deterministic transition map over `RecoveryCaseStatus` (`NEW→DIAGNOSING→PREDICTED→STRATEGY_SELECTED→POLICY_CHECK→AWAITING_APPROVAL→EXECUTING→VERIFYING→RECOVERED/FAILED→…→STOPPED`), `ValueError` on invalid transitions, `is_terminal`. `NEXT_STRATEGY` treated as a transition label; enum unchanged.
- **`engine/decision_engine.py`** — `Decision` + `EvaluatedStrategy` dataclasses and `DecisionEngine`:
  - `expected_net_recovery = P × amount − cost` in integer paise (model-scored 5 strategies; `DISCOUNT_OFFER` only when a discount is offered).
  - **WAIT** (AC-04): compares now vs the merchant's configurable window; selects WAIT with `recommended_at` when future EV > now.
  - **STOP**: selects STOP when max expected net < 0.
  - `decide()` persists one `AgentDecision` + one `AuditLog` and advances `RecoveryCase.status` (AC-08); JSON-sanitizes numpy/pandas scalars.
- **`tests/test_decision_engine.py`** — 5 DB-backed tests (transitions, EV paise, persist+audit, STOP, WAIT).

## Verification
- `python -m pytest tests/test_decision_engine.py -q` → **5 passed**.
- Full suite (Phase 2 + 3) → **29 passed**.

## Notes
- Fixed: free/fallback strategies (`PAYMENT_LINK`, `HUMAN_ESCALATION`, rate-0 `DISCOUNT_OFFER`) made STOP unreachable and dominated selection — restricted scoring to model-backed strategies; `DISCOUNT_OFFER` gated on `discount_rate > 0`.
- Fixed: numpy scalar JSON serialization; detached-ORM merge for case persistence.
