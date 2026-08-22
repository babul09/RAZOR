# Repository Structure

**Analysis Date:** 2026-08-22

## Top-Level Layout
- `config.py` - environment-backed application settings.
- `pyproject.toml` and `requirements.txt` - dependency and packaging declarations.
- `.env.example` - local environment variable template.
- `db/` - SQLAlchemy base, session factory, and ORM models.
- `alembic/` - migration environment and initial schema revision.
- `scripts/` - currently package marker only.
- `simulation/` - currently package marker and empty data directory.
- `.planning/` - project requirements, roadmap, state, and research artifacts.

## Database Files
- `db/base.py` defines `Base`.
- `db/database.py` defines `engine`, `SessionLocal`, and `get_db`.
- `db/models.py` contains enums and all current ORM entities.
- `alembic/versions/001_initial_schema.py` creates the initial thirteen-table schema.

## Naming and Organization
- Python modules use lowercase snake_case names.
- ORM classes use PascalCase singular names.
- Database tables use lowercase snake_case plurals.
- Monetary columns use the `_paise` suffix.
- JSON payload columns use the `_json` suffix.

## Planned but Missing Locations
- The project overview describes future `api/`, `agents/`, `ml/`, `engine/`, `integrations/`, and richer `simulation/` modules.
- No `tests/` directory, CI configuration, frontend directory, or application launcher is present.

<!-- refreshed: 2026-08-22 -->