# Codebase Concerns

**Analysis Date:** 2026-08-22

## Completeness Risks
- The repository currently contains schema/configuration foundations only; the planned API, agent, ML, policy, execution, analytics, and simulation behavior is absent.
- There is no runnable `simulate.py` or equivalent entry point despite the project state naming simulation validation as the next step.
- There are no tests, so model/migration regressions can pass unnoticed.

## Security Risks
- `config.py` has a development `secret_key` fallback that must never be used in production.
- `.env.example` documents credentials and connection strings; real `.env` files must stay untracked.
- No authentication, authorization, secret rotation, request validation, or rate limiting exists yet.
- Future LLM and external integration payloads need redaction and strict audit boundaries.

## Data Integrity Risks
- ORM models use naive `datetime.utcnow` defaults rather than timezone-aware timestamps.
- Monetary correctness depends on every future service preserving integer paise semantics.
- Several relationships lack explicit cascade behavior, indexes, or uniqueness beyond the current policy/profile constraints.
- `source_id` on recovery cases is documented as a source reference but is not a foreign key.

## Operational Risks
- `db/database.py` eagerly creates an engine during import and assumes a usable PostgreSQL URL.
- No health checks, migration startup policy, worker monitoring, or structured logging are present.
- Redis and Celery are declared but unconfigured beyond a URL setting.

## Architecture Risks
- The roadmap describes a policy hard gate, but no policy engine currently enforces it.
- The LLM is intended for diagnosis/strategy only, but no execution boundary exists yet to enforce that rule.
- The initial migration and ORM defaults should be kept synchronized as the schema evolves.

<!-- refreshed: 2026-08-22 -->