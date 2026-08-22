# Plan 06-02 Summary — Experiment Engine + Experiments API + Weights

**Phase:** 06-recovery-memory · **Plan:** 02 · **Wave:** 2
**Status:** COMPLETE

## What was built

- **`engine/experiment_engine.py`** — `ExperimentEngine`:
  - `create_experiment(session, name, arms, merchant_id)` — validates traffic sums to 100, persists `Experiment` + `ExperimentArm`.
  - `allocate(arms, key, seed)` — deterministic weighted traffic allocation.
  - `record_arm_metric(session, arm_id, recovered, revenue_paise)` — per-arm attempts/recoveries/revenue.
  - `compute_strategy_weights(session)` — normalized weights from per-arm recovery rates (best → 1.0); `apply_weights(engine, weights)` → `DecisionEngine.set_strategy_weights` (FR-12 feedback).
- **`api/routers/experiments.py`** — `POST /api/experiments` (create, 400 on bad traffic), `GET /api/experiments/weights`, enhanced `GET /api/experiments` (per-arm recovery_rate, AC-07).
- **`api/schemas.py`** — `ExperimentCreateRequest/Response`, `ExperimentArmCreate`, recovery_rate on metric.
- **`scripts/seed_experiment.py`** — idempotent demo experiment (control/retry/whatsapp/upi_switch).
- **`tests/test_experiment_engine.py`** — 7 tests.

## Verification
- `python -m pytest tests/test_experiment_engine.py -q` → **7 passed**.
- Full suite → **65 passed**.
- `python scripts/seed_experiment.py` → created demo experiment (idempotent on rerun); `GET /api/experiments` shows 4 arms; `GET /api/experiments/weights` returns `{}` until metrics recorded.

## Notes
- Fix: `Experiment.merchant_id` is required FK → added `merchant_id` param/schema/fixture.
