# Phase 6: Recovery Memory + Experiment Engine — Research

**Researched:** 2026-08-22
**Domain:** Learning loop (recovery memory + profile updates) and A/B experiment engine with decision feedback.
**Confidence:** HIGH

## Locked Decisions (user-confirmed)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Memory store | **New `recovery_memory` table** | Explicit FR-11 learning loop; alembic migration 002. |
| Profile update | **Celery `update_profile` task** | Async recompute of `CustomerRecoveryProfile` per-channel rates (Redis worker). |
| Strategy weights | **EV multiplier in DecisionEngine** | Experiment-derived weights scale expected net recovery (FR-12 "self-optimizing"). |
| Experiment setup | **POST /api/experiments** | Create experiments at runtime (arms with traffic_percent + strategy). |

## Environment (verified)

- PostgreSQL + Redis running; Celery app in `agents/celery_app.py` (tasks in `agents/tasks.py`).
- Alembic env imports `db.models` (metadata populated); migration `001` hand-written → next revision `002`.
- Existing models: `RecoveryCase`, `RecoveryOutcome` (case_id, revenue/cost/net paise, recovery_method), `CustomerRecoveryProfile` (per-channel attempts/successes: retry, whatsapp, email, upi_switch, discount + overall_recovery_probability), `Experiment`, `ExperimentArm` (arm_name, traffic_percent, strategy, attempts, recoveries, revenue_recovered_paise).
- `engine/outcome_verifier.py` records `RecoveryOutcome` and sets case RECOVERED/FAILED.
- `engine/decision_engine.py` `expected_net_recovery = P × amount − cost`.

## Requirements

- **FR-11** Recovery Memory: after each resolved case store `(customer, failure_type, strategy, outcome)`; update customer per-channel success rates; next case uses updated probabilities.
- **FR-12** A/B Experiment Engine: define experiments, allocate % of similar failures to control vs treatment; track per-arm recovery rate / revenue / cost / net; update strategy weights from results.
- **AC-07** Experiment engine shows per-arm recovery-rate differences.

## Design

### `recovery_memory` table (migration 002)
- Columns: `id` (uuid string), `customer_id` (FK), `failure_type` (str), `strategy` (str), `outcome` (str RECOVERED/FAILED), `recovered` (bool), `amount_paise` (BigInteger), `created_at`.
- Model `RecoveryMemory` in `db/models.py`.

### `engine/recovery_memory.py`
- `record_outcome(session, case, strategy, recovered, amount_paise)` — insert `RecoveryMemory` row.
- `update_profile(session, customer_id)` — recompute `CustomerRecoveryProfile` per-channel attempts/successes and `overall_recovery_probability` from `recovery_memory` rows (grouped by strategy), update the row.
- Called by Celery task `update_profile(customer_id)` in `agents/tasks.py`; integrated after a case resolves (outcome verifier records memory, then dispatches profile update).

### DecisionEngine strategy weights (EV multiplier)
- `DecisionEngine(..., strategy_weights: dict[str, float] | None = None)` (default all 1.0).
- `expected_net_recovery` multiplies `probability` by `weight` (clamped to [0,1]) before `× amount − cost`; `set_strategy_weights(...)` to update.

### `engine/experiment_engine.py`
- `create_experiment(session, name, arms)` — insert `Experiment` + `ExperimentArm` rows (validated traffic_percent sums to 100).
- `allocate(strategy, seed)` — deterministic traffic allocation to experiment arms (weighted by traffic_percent).
- `record_arm_metric(session, arm_id, recovered, revenue_paise)` — increment arm attempts/recoveries/revenue.
- `compute_strategy_weights(session, experiments)` — per-arm recovery rate → normalized strategy weight dict (documented rule; higher rate → higher weight; missing strategies default 1.0).

### API
- `POST /api/experiments` — create an experiment (name + arms); returns created experiment + arms.
- `GET /api/experiments` — enhanced to include per-arm metrics (attempts, recoveries, recovery_rate, recovered_paise) — already partially present in Phase 5.
- `GET /api/experiments/weights` — expose computed strategy weights (used by the decision engine / dashboard).

## Risk / mitigation
- **New table** → alembic migration 002 hand-written; `alembic upgrade head` before running.
- **Weight feedback** → clamp probability to [0,1]; weights default 1.0; no negative weights.
- **Traffic allocation** → deterministic (hash of key) so tests are stable.
- **Async profile update** → eager-mode tests + real-broker integration check (skippable).
- **Money** → integer paise (NFR-03).
