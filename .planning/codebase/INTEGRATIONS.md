# External Integrations

**Analysis Date:** 2026-08-22

## Database
- PostgreSQL is the intended persistent store.
- `config.py` supplies `settings.database_url`.
- `db/database.py` creates the SQLAlchemy engine with `pool_pre_ping=True`, pool size 10, and max overflow 20.
- `db/database.py:get_db` exposes a generator dependency suitable for FastAPI request lifecycles.
- `alembic/env.py` overrides the migration URL from application settings.

## Cache and Background Work
- Redis is configured through `settings.redis_url` but no Redis client or Celery app is implemented yet.
- Celery is declared in `pyproject.toml` and `requirements.txt` for planned event-driven workflows.

## LLM
- Gemini is the selected provider in `.planning/config.json` and `config.py` exposes `gemini_api_key`.
- No Gemini client, prompt, retry policy, or response validation code is present.
- Project architecture explicitly keeps LLM diagnosis/strategy outside the payment execution path.

## Payment and Messaging
- No payment gateway SDK, adapter, webhook route, WhatsApp integration, email provider, or payment-link client exists yet.
- Planned recovery channels are represented as policy data and strategy enum values in `db/models.py`.

## HTTP and UI
- FastAPI, Uvicorn, and httpx are dependencies, but no API routes or ASGI entry point exist.
- The project plan names Next.js, React, Tailwind, and Recharts for a future dashboard; no frontend directory is present.

## Integration Contract Risks
- Environment defaults include development credentials and local service endpoints.
- External service calls will need explicit timeouts, idempotency, audit logging, and failure handling before execution code is added.

<!-- refreshed: 2026-08-22 -->