# Plan 05-02 Summary — Ingest + Risk Engine + Celery Simulation + Experiments

**Phase:** 05-fastapi-backend · **Plan:** 02 · **Wave:** 2
**Status:** COMPLETE

## What was built

- **`engine/risk_engine.py`** — FR-02 risk score: `compute_risk_score(value, severity, probability, value_factor)` (integer), `build_severity`, `customer_value_factor`.
- **`api/routers/events.py`** — `POST /api/events/ingest`: idempotent by `event_id` (Payment PK), validates event_type (400), creates `Payment` + `RecoveryCase` (priority = risk score) on `payment.failed` (FR-01/FR-02).
- **`agents/tasks.py`** — `run_simulation(n_events, seed, hour)` Celery task returning baseline/RAZOR comparison dict (FR-13).
- **`api/routers/simulation.py`** — `POST /api/simulation/run` → `{job_id}`; `GET /api/simulation/status/{job_id}` polls Celery Redis backend (PENDING/SUCCESS/FAILURE).
- **`api/routers/experiments.py`** — `GET /api/experiments` reads Experiment + ExperimentArm (empty ok).
- **`api/main.py`** — registered events/simulation/experiments routers.
- **`tests/test_api.py`** — risk formula, ingest creates case + idempotent, unsupported type 400, eager simulation, experiments.

## Verification
- `python -m pytest tests/test_api.py -q` → **12 passed**.
- Full suite → **53 passed**.
- Real-broker smoke: started a Celery worker (`--pool=solo`), `run_simulation.delay(100)` → **SUCCESS** (incremental ₹60.1L); `POST /api/simulation/run` + status → SUCCESS via API; `/health` ok; `/api/experiments` 200.

## Notes
- Simulation is async (Celery + Redis backend), meeting the chosen "Celery async job" decision and FR-13 hero-moment path.
