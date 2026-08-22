# Submission Checklist

Use this to confirm RAZOR is demo-ready before submitting.

## Build & Tests
- [ ] `python -m pytest -q` → **69 passed** (DB + Redis running)
- [ ] `cd web && npm run build` → succeeds
- [ ] `alembic upgrade head` applied (schema incl. `recovery_memory`)
- [ ] `python scripts/seed_db.py` and `python scripts/seed_experiment.py` idempotent

## Live Stack
- [ ] PostgreSQL running + migrated
- [ ] Redis running (`redis-cli ping` → PONG)
- [ ] Backend: `uvicorn api.main:app` → `/health` ok
- [ ] Dashboard: `cd web && npm run dev` → loads live data (no mock fallback)

## Demo Flow (10 steps)
- [ ] `python -m pytest tests/test_demo_flow.py` → passes
- [ ] Generate events → ₹ at risk shown
- [ ] Diagnosis outputs structured JSON (fallback ok without Gemini key)
- [ ] Strategy breakdown shown
- [ ] Simulation runs → ₹ recovered > baseline
- [ ] Drill-down timeline + audit trail
- [ ] Policy blocks discount > max_discount_percent
- [ ] Learning loop updates profile
- [ ] Dashboard headline `+₹7.22L incremental revenue` prominent

## Deploy (manual)
- [ ] Backend on Railway (start command, DATABASE_URL, REDIS_URL, CORS)
- [ ] Frontend on Vercel (root `web`, `NEXT_PUBLIC_API_URL`)
- [ ] Managed PostgreSQL migrated
- [ ] Live dashboard + API verified

## Final Package
- [ ] Record 2-3 min demo video per `docs/WALKTHROUGH.md`
- [ ] README + architecture diagram up to date
- [ ] Repo clean (no secrets, no `node_modules`/`.venv` committed)
- [ ] Commit + tag the release
