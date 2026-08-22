# Deployment Guide

RAZOR deploys as three managed services:

- **Frontend** — Next.js dashboard → **Vercel**
- **Backend** — FastAPI API + Celery workers → **Railway**
- **Data** — **Managed PostgreSQL** (e.g., Railway Postgres or Neon)

## 1. Managed PostgreSQL

Provision a managed PostgreSQL and note the connection string
(`postgresql://USER:PASS@HOST:PORT/DB`). Run the migrations once:

```bash
source .venv/bin/activate
export DATABASE_URL="postgresql://USER:PASS@HOST:PORT/DB"
alembic upgrade head
```

## 2. Backend on Railway

1. Create a **Railway** project from the repo (or a backend subfolder).
2. **Start command:** `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
3. **Environment variables:**
   - `DATABASE_URL` (managed Postgres)
   - `REDIS_URL` (Railway Redis, for Celery/SSE cache)
   - `GEMINI_API_KEY` (optional, enables live diagnosis)
4. Add a separate **Celery worker** service: `celery -A agents.celery_app worker --loglevel=info`.
5. Set **CORS** to allow the frontend origin (see `api/main.py` `allow_origins`).

## 3. Frontend on Vercel

1. Import the repo in **Vercel**.
2. **Root directory:** `web`.
3. Framework preset auto-detected (Next.js).
4. **Environment variable:** `NEXT_PUBLIC_API_URL` = the Railway backend URL
   (e.g., `https://your-backend.up.railway.app`).
5. Deploy.

## 4. Post-deploy checks

- `GET /health` on the backend returns `{"status":"ok"}`.
- Dashboard loads Overview from the live API (no mock fallback).
- Run a simulation from the dashboard and see results.

> Keep secrets in environment variables only — never commit credentials.
