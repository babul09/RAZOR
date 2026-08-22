# Plan 06-01 Summary — Recovery Memory + Profile Recompute + Weighted EV

**Phase:** 06-recovery-memory · **Plan:** 01 · **Wave:** 1
**Status:** COMPLETE

## What was built

- **`db/models.py`** — `RecoveryMemory` model (FR-11 learning tuple: customer, failure_type, strategy, outcome, recovered, amount_paise).
- **`alembic/versions/002_recovery_memory.py`** — migration `002` (down `001`) creating the table + customer_id index; applied.
- **`engine/recovery_memory.py`** — `record_outcome(...)` + `update_profile(session, customer_id)` recomputing `CustomerRecoveryProfile` per-channel attempts/successes + overall probability from memory (deterministic; `expire_on_commit=False`).
- **`agents/tasks.py`** — Celery `update_profile(customer_id)` task.
- **`engine/decision_engine.py`** — `strategy_weights` (default 1.0) + `set_strategy_weights()`; `expected_net_recovery` and `evaluate_strategies` scale probability by weight (clamped [0,1]) — the FR-12 feedback hook.
- **`tests/test_recovery_memory.py`** — 5 DB-backed tests.

## Verification
- `python -m pytest tests/test_recovery_memory.py -q` → **5 passed**.
- Full suite → **65 passed**.
- Migration 002 applied; `recovery_memory` table present.

## Notes
- Fix: detached-instance expiry → `session.expire_on_commit = False` in `update_profile`.
