# Architecture

**Analysis Date:** 2026-08-22

## Current Shape
- The implemented code is a persistence foundation rather than a running service.
- `config.py` is the settings boundary.
- `db/base.py` owns the SQLAlchemy declarative base.
- `db/models.py` owns the domain schema and relationships.
- `db/database.py` owns engine/session construction.
- `alembic/env.py` connects application settings and model metadata to migrations.

## Domain Model
- Merchant ownership anchors customers, policies, experiments, and recovery data.
- A customer owns payments, payment attempts, recovery cases, and one recovery profile.
- A recovery case owns actions, agent decisions, outcomes, and audit logs.
- Experiments contain experiment arms for strategy comparisons.
- Policies provide merchant-specific hard limits and allowed channels.

## Intended Data Flow
1. A failed payment becomes a recovery case.
2. Diagnosis and prediction enrich the case.
3. A strategy is selected and recorded as an agent decision.
4. A policy check gates execution or human approval.
5. Recovery actions produce outcomes and audit events.
6. Profiles and experiments collect learning/measurement data.

## Safety Boundaries
- `RecoveryCaseStatus` models an explicit lifecycle from `NEW` through `RECOVERED`, `FAILED`, or `STOPPED`.
- `RecoveryStrategy.WAIT` and `STOP` are modeled as valid decisions.
- `Policy` stores discount, amount, contact, channel, approval, and stop-on-success controls.
- `AgentDecision.policy_check_passed` provides an audit field for the policy gate.

## Entry Points
- No executable API, worker, CLI, or simulation entry point is currently implemented.
- Database migration execution is the only operational path represented by repository code.

<!-- refreshed: 2026-08-22 -->