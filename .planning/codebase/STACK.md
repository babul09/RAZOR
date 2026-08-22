# Technology Stack

**Analysis Date:** 2026-08-22

## Runtime
- Python `>=3.11` is declared in `pyproject.toml`.
- Packaging uses setuptools with package discovery rooted at `.`.
- Configuration is loaded at import time from `.env` through `pydantic-settings` in `config.py`.

## Implemented Frameworks
- SQLAlchemy 2.x provides the declarative ORM in `db/base.py` and `db/models.py`.
- Alembic manages database migrations through `alembic.ini`, `alembic/env.py`, and `alembic/versions/001_initial_schema.py`.
- Pydantic Settings provides typed environment-backed application settings in `config.py`.

## Declared Application Dependencies
- FastAPI and Uvicorn are declared for the planned HTTP API.
- pandas, scikit-learn, and XGBoost are declared for prediction and simulation work.
- Google Generative AI is declared for Gemini diagnosis and strategy support.
- Celery and Redis are declared for event-driven/background processing.
- httpx, Rich, tabulate, Faker, and pytest support integrations, CLI output, synthetic data, and tests.
- PostgreSQL is the configured database target via `psycopg2-binary`.

## Configuration
- `DATABASE_URL` defaults to a local PostgreSQL database in `config.py`.
- `REDIS_URL` defaults to local Redis.
- `GEMINI_API_KEY`, `SECRET_KEY`, and `ENVIRONMENT` are supported settings.
- `.env.example` documents the expected environment variable names.

## Conventions
- Monetary fields use integer paise (`BigInteger`) rather than floating-point currency values.
- UUIDs are represented as generated string values in the current models.
- PostgreSQL-specific `JSONB` and `UUID` imports are available; current identifiers use `String(36)`.

## Current Boundary
- No FastAPI application module, worker, ML implementation, frontend, or runnable simulation entry point exists in the repository yet.

<!-- refreshed: 2026-08-22 -->