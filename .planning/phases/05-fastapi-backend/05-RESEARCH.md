# Phase 5: FastAPI Backend — Research

**Researched:** 2026-08-22
**Domain:** FastAPI REST API over PostgreSQL + Redis/Celery, serving the dashboard and demo.
**Confidence:** HIGH

## Locked Decisions (user-confirmed)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Auth | **None** | Open demo/dashboard endpoints (hackathon). |
| Simulation run | **Celery async job** | POST dispatches a Celery task, returns job id; client polls status (Celery backend = Redis). |
| Experiments endpoint | **Read DB** | `experiments`/`experiment_arms` may be empty until Phase 6 fills them. |
| Risk engine (FR-02) | **Include risk scoring now** | `risk = transaction_value × failure_severity × recovery_probability × customer_value_factor`, computed on `payment.failed` ingest. |

## Environment (verified)

- PostgreSQL running (`razor`/`razor_db`, migrated); Redis running (`redis://localhost:6379/0`, PONG).
- FastAPI, uvicorn, httpx installed; `pip check` clean.
- `db/database.py` provides `SessionLocal` + `get_db()` FastAPI dependency.
- Existing models: `RecoveryCase` (has `source_type`, `source_id`, `amount_at_risk_paise`, `failure_code`, `status`, `priority`, timestamps), `RecoveryAction`, `RecoveryOutcome`, `AgentDecision`, `AuditLog`, `Experiment`, `ExperimentArm`, `Customer`, `Payment`.
- Celery app in `agents/celery_app.py` (broker/backend = Redis), tasks in `agents/tasks.py`.
- Simulators: `simulation/baseline_simulator.py`, `simulation/razor_simulator.py`, `simulation/evaluator.py` (comparison helpers), `SyntheticDataGenerator`.

## Requirements

- **FR-01** Event ingestion: types (`payment.failed`, `payment.success`, `checkout.abandoned`, `invoice.overdue`, `subscription.failed`, `refund.created`, `dispute.created`); **idempotent** (duplicate events do not duplicate cases).
- **FR-02** Revenue risk engine: on `payment.failed` auto-create `recovery_case`; risk score prioritizes cases.
- **FR-13** Simulation engine: comparison table (baseline vs RAZOR) — demo hero moment.
- **FR-14** Dashboard data: overview, live queue, agent activity, strategy performance, simulation.
- **NFR-01** API response < 500ms for dashboard queries → Redis caching for analytics.
- **NFR-03** Integer paise money.

## API surface

| Method | Path | Purpose |
|--------|------|---------|
| GET | /health | liveness |
| GET | /api/recovery/cases | paginated recovery queue (status filter) |
| GET | /api/recovery/cases/{id} | case detail + decision timeline |
| POST | /api/simulation/run | dispatch Celery simulation task -> job_id |
| GET | /api/simulation/status/{job_id} | poll Celery task status/result |
| GET | /api/analytics/overview | ₹ at risk, recovered, recovery rate (Redis-cached) |
| GET | /api/analytics/strategies | per-strategy performance |
| GET | /api/experiments | A/B experiment results (reads DB) |
| POST | /api/events/ingest | idempotent webhook -> creates payment + recovery_case + risk score |

## Design

### App layout
- `api/main.py` — FastAPI app, include routers, `TestClient`-usable.
- `api/routers/{health,recovery,analytics,simulation,events,experiments}.py`
- `api/schemas.py` — Pydantic response models.

### Risk engine (`engine/risk_engine.py`)
- `compute_risk_score(transaction_value_paise, failure_severity, recovery_probability, customer_value_factor) -> int`; deterministic, documented severity/factor tables; integer score. On ingest, create `recovery_case` with `priority` = risk score.

### Simulation async
- New Celery task `run_simulation(n_events, seed, hour)` in `agents/tasks.py` that runs baseline + RAZOR simulators and returns the comparison dict (uses existing simulators; no DB/network needed beyond Redis broker).
- `POST /api/simulation/run` → `run_simulation.delay(...)` → returns `{ job_id }`; `GET /api/simulation/status/{job_id}` reads the Celery result backend (Redis) → PENDING/SUCCESS/FAILURE + result.

### Redis caching (NFR-01)
- `/api/analytics/overview` cached in Redis with a short TTL; on miss, compute from DB and store.

## Risk / mitigation
- **No auth** → open demo only; document that production needs auth (out of scope).
- **Celery job result availability** → status endpoint returns PENDING/FAILURE gracefully; tests run the task eagerly + a real-broker integration check.
- **Idempotency** → `events/ingest` dedupes by event id (unique-ish check / on-conflict) so duplicates don't create duplicate cases.
- **Analytics NFR-01** → Redis cache bounds DB query cost.
- **Money** → all money integer paise (NFR-03).
