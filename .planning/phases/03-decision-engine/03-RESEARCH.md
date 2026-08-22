# Phase 3: Decision Engine & Policy Guardrails — Research

**Researched:** 2026-08-22
**Domain:** Deterministic strategy selection, policy enforcement, and state management over PostgreSQL.
**Confidence:** HIGH

## Locked Decisions (user-confirmed)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Audit logging | **Direct PostgreSQL writes** | User started role/db; schema migrated (14 tables); `agent_decisions` + `audit_logs` written directly. |
| Outcome verifier (FR-10) | **Include in Phase 3** | Simulator-backed verify completes the decide→execute→verify loop offline. |
| WAIT timing | **Configurable per-merchant window** | High-value window (default 19–22) read from merchant policy config. |
| Demo delivery | **Seed DB + CLI** | `scripts/demo_decision_engine.py` reads seeded `recovery_cases`, runs the engine, prints policy-block and WAIT decisions. |

## Environment (verified)

- PostgreSQL 18.6 running on localhost:5432; role `razor` / db `razor_db` (config.py default URL).
- `alembic upgrade head` applied — 14 tables present including `agent_decisions`, `audit_logs`, `recovery_cases`, `recovery_outcomes`, `recovery_actions`, `policies`.
- Phase 2 delivers `RecoveryModel.predict_proba(features, strategy) -> float in [0,1]` and artifact `ml/artifacts/recovery_model.joblib`.

## Key existing assets

- `db/models.py`: `RecoveryStrategy` enum (9 values), `RecoveryCaseStatus` enum (11 values), `Policy` (7 guardrail fields), `AgentDecision`, `AuditLog`, `RecoveryAction`, `RecoveryOutcome`, `RecoveryCase`.
- `simulation/razor_simulator.py`: `STRATEGY_COSTS_PAISE` (RETRY 200, PAYMENT_METHOD_SWITCH 300, WHATSAPP_REMINDER 100, EMAIL_REMINDER 50, PAYMENT_LINK 0, DISCOUNT_OFFER None→dynamic, HUMAN_ESCALATION 25000, WAIT 0, STOP 0).
- Phase 1 `select_strategy` already encodes segment-based selection (A→retry/wait, B→switch, C→whatsapp, D→escalation/retry, E→stop).

## Design

### Strategy engine (FR-06)
- `expected_net_recovery_paise = P(recovery | strategy) × amount_paise − cost_paise`.
- Probabilities from `RecoveryModel.predict_proba`; costs from `STRATEGY_COSTS_PAISE`; discount cost derived from policy `max_discount_percent` (bounded).
- **WAIT**: evaluate now vs the merchant's high-value window (configurable hours). If a future-window action's expected net > best current action's, select `WAIT` with a `recommended_at` timestamp. (AC-04)
- **STOP**: if `max(expected_net) < 0` across all strategies, select `STOP`. (no action)
- Result is a `Decision` dataclass; writes `AgentDecision` (with strategies evaluated, selected strategy, reasoning, policy_check_passed) + `AuditLog`, and updates `RecoveryCase.status`.

### Policy engine (FR-07) — hard gate, 7 checks
- Merchant policy loaded from YAML (with DB `Policy` fallback/sync).
- Checks: `max_discount_percent`, `max_automated_amount_paise`, `max_contacts_count`, `max_contacts_window_days`, `require_human_approval_above_paise`, `allowed_channels`, `stop_if_payment_succeeds`.
- On block → route to `AWAITING_APPROVAL`, log reason to `audit_logs`. (AC-05)

### State machine (FR-09)
- Deterministic transitions over `RecoveryCaseStatus`: `NEW → DIAGNOSING → PREDICTED → STRATEGY_SELECTED → POLICY_CHECK → AWAITING_APPROVAL → EXECUTING → VERIFYING → [RECOVERED | FAILED → NEXT_STRATEGY → STOPPED]`.
- Every transition logged to `audit_logs`.

### Outcome verifier (FR-10) + action executor (FR-08, minimal)
- Simulator-backed `ActionExecutor` (retry/whatsapp/email/upi-switch) using the oracle; `OutcomeVerifier.verify(...)` records `recovery_rate`, `revenue_recovered`, `cost_of_recovery`, `net_revenue_recovered` to `recovery_outcomes` and updates the case.

## Risk / mitigation
- **Tests need live PostgreSQL** (user's explicit choice). Tests use `SessionLocal` + cleanup; plan documents the prerequisite (postgres running + migrated).
- **Discount cost is dynamic** — bounded by `max_discount_percent` × amount; treat as cost in EV, no float money.
- **12-state claim vs 11-state enum** — reconcile by treating `NEXT_STRATEGY` as a transition label (FAILED→next), keeping the enum unchanged to avoid schema migration.
