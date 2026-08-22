# Deployment Guide — Full Stack (FastAPI + Celery + Redis + Postgres + Next.js)

Deploy RAZOR as four managed services:

| Service | Runs | Host |
|---------|------|------|
| **Frontend** | Next.js dashboard | Vercel |
| **API** | FastAPI (`uvicorn api.main:app`) | Railway |
| **Worker** | Celery (`agents.celery_app`) | Railway (separate service) |
| **Data** | PostgreSQL + Redis | Managed (Railway / Neon / Upstash) |

> This guide assumes you want **Celery** (async diagnosis/explanation) **and**
> **Gemini** (LLM diagnosis). The demo works without both, but this is the full config.

---

## 1. Local prerequisites (already done here)

- Python venv: `source .venv/bin/activate`
- PostgreSQL running (role `razor` / db `razor_db`)
- Redis running (Celery broker): `redis-cli ping` → `PONG`
- `.env` with real keys.

### Critical: a **valid** Gemini API key
The agents use Gemini for diagnosis/explanation; if the key is missing/invalid they
**silently fall back to rule-based** output. Get a key at
**https://aistudio.google.com/apikey**, then set it in `.env`:
```dotenv
GEMINI_API_KEY=AIza...
```
Sanity-check it works:
```bash
python -c "import google.generativeai as g; g.configure(api_key=__import__('config').settings.gemini_api_key); print(g.GenerativeModel('gemini-1.5-flash').generate_content('reply OK').text)"
```
> Models default to `gemini-1.5-flash`. If you get `API_KEY_INVALID`, the key is bad —
> there's no amount of redeploying that fixes that; replace the key.

---

## 2. Managed PostgreSQL

Provision managed Postgres, note the URL, run migrations once:
```bash
export DATABASE_URL="postgresql://USER:PASS@HOST:PORT/DB"
alembic upgrade head
```
Seed the dashboard data (the dashboard reads the DB):
```bash
python scripts/demo_data.py --events 800 --reset
```

---

## 3. Backend API (Railway)

1. Create a **Railway** project from the repo.
2. **Start command:** `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
3. **Environment variables:**

   | Var | Value |
   |-----|-------|
   | `DATABASE_URL` | managed Postgres URL |
   | `REDIS_URL` | Railway Redis URL |
   | `GEMINI_API_KEY` | valid Gemini key (enables LLM diagnosis) |
   | `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` | (optional) live Razorpay tab |
   | `SECRET_KEY` | random secret |
   | `ENVIRONMENT` | `production` |

---

## 4. Celery Worker (Railway, separate service)

Celery runs the **async Gemini diagnosis/explanation** tasks. It must share the same
`DATABASE_URL` and `REDIS_URL`.

1. Add a second Railway service for the repo.
2. **Start command:**
   ```bash
   celery -A agents.celery_app worker --loglevel=info --concurrency=2
   ```
3. Same env vars as the API (`DATABASE_URL`, `REDIS_URL`, `GEMINI_API_KEY`).

> **How Celery is triggered:** when the API ingests a `payment.failed` event, it calls
> `dispatch_diagnosis(case_id)` which enqueues `diagnose_case` on the broker. The worker
> picks it up, runs Gemini (or rule-based fallback), and writes an `AgentDecision` +
> `AuditLog`. If the broker is down, the API runs it inline so nothing is lost.

---

## 5. Frontend (Vercel)

1. Import the repo in Vercel.
2. **Root directory:** `web`
3. Framework preset auto-detected (Next.js).
4. **Environment variable:** `NEXT_PUBLIC_API_URL` = your Railway backend URL
   (e.g., `https://your-backend.up.railway.app`).
5. Deploy.

---

## 6. Post-deploy checks

```bash
# API up?
curl -s https://<api>/health                                   # {"status":"ok"}
# Razorpay configured?
curl -s https://<api>/api/razorpay/health
# Ingestion triggers a Celery diagnosis (watch worker logs for a success line)
curl -s -X POST https://<api>/api/events/ingest \
  -H 'Content-Type: application/json' \
  -d '{"event_id":"evt_<uuid>","event_type":"payment.failed","merchant_id":"merchant_001",
       "customer_id":"<real customer id>","amount_paise":450000,
       "payment_method":"card","failure_code":"card_declined"}'
# Dashboard loads from the live API (no mock fallback)
curl -s -o /dev/null -w "%{http_code}\n" https://<vercel>.vercel.app
```

---

## 7. Local run with Celery + Gemini (before you deploy)

```bash
# Terminal 1 — API
source .venv/bin/activate && uvicorn api.main:app --port 8000

# Terminal 2 — Celery worker (needs Redis)
source .venv/bin/activate && celery -A agents.celery_app worker --loglevel=info

# Terminal 3 — Dashboard
cd web && npm run dev -- -p 3050
```
Then ingest a `payment.failed` event (above) and confirm the worker log shows a
**Gemini** diagnosis (not just rule-based).

---

## 8. Secrets checklist
- [ ] `GEMINI_API_KEY` is **valid** (tested with a live call)
- [ ] `DATABASE_URL` reachable; migrations applied
- [ ] `REDIS_URL` reachable from both API and worker
- [ ] `RAZORPAY_KEY_ID/SECRET` (optional)
- [ ] `NEXT_PUBLIC_API_URL` points at the backend
- [ ] CORS allows the frontend origin (backend defaults to allow-all for the demo;
      tighten in production)

