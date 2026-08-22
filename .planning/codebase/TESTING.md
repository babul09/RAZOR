# Testing

**Analysis Date:** 2026-08-22

## Current State
- pytest is declared as a dependency in `pyproject.toml` and `requirements.txt`.
- No `tests/` directory or test modules are present.
- No CI workflow, coverage configuration, or test command is documented in the repository.

## Highest-Value Initial Tests
- Verify settings load from environment variables and `.env` with safe precedence.
- Verify ORM metadata contains the entities represented by the initial migration.
- Verify `get_db` closes sessions on normal completion and exceptions.
- Verify monetary values remain integer paise at model/service boundaries.
- Verify policy constraints cover discount, amount, contacts, channels, approval, and stop-on-success behavior.
- Verify recovery status and strategy transitions reject invalid execution paths.

## Database Testing
- Prefer PostgreSQL-compatible integration tests for JSONB and migration behavior.
- Test `alembic/versions/001_initial_schema.py` upgrade and downgrade against a disposable database.
- Test relationship ownership and unique constraints for policies and recovery profiles.

## Planned System Testing
- Unit tests should cover deterministic feature engineering, policy evaluation, and outcome calculations.
- Contract tests should cover payment, notification, and future Gemini adapters.
- Simulation tests should compare RAZOR metrics with the baseline using fixed random seeds.
- End-to-end tests should verify audit records are written for every agent decision.

## Testability Gaps
- No application entry point or service layer exists to exercise the declared FastAPI/Celery stack.
- No fixtures, factories, sample data, or test database settings are present.

<!-- refreshed: 2026-08-22 -->