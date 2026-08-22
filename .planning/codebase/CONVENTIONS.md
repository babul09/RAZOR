# Coding Conventions

**Analysis Date:** 2026-08-22

## Python Style
- Modules begin with short docstrings describing their RAZOR responsibility.
- Imports are grouped by standard library, third-party packages, and local modules.
- Classes and enums use PascalCase; functions, settings, and columns use snake_case.
- Type annotations are used for `get_db` and selected configuration/database interfaces.
- Existing code uses four-space indentation and descriptive names.

## ORM Conventions
- Models inherit from `Base` from `db.base`.
- Tables declare `__tablename__` explicitly.
- Primary keys are generated UUID strings using `uuid.uuid4()`.
- Relationships use paired `back_populates` names.
- Defaults are declared on columns for timestamps, statuses, counters, and policy values.

## Domain Conventions
- Enum values are uppercase strings for lifecycle statuses and strategies.
- All money is integer paise; `Float` is used only for probabilities, percentages, and model metrics.
- JSONB fields store flexible decision, experiment, audit, and policy payloads.
- `UniqueConstraint` enforces one recovery profile and one policy per relevant owner.

## Error Handling
- The current persistence layer does not define custom exceptions or transaction helpers.
- `get_db` guarantees session closure with `try/finally`.
- API-level validation, retry behavior, and integration error handling are not implemented yet.

## Change Guidance
- Preserve the paise convention and policy gate semantics when adding services.
- Keep model metadata imports synchronized with `alembic/env.py`.
- Add tests alongside new domain or execution behavior before widening the service surface.

<!-- refreshed: 2026-08-22 -->