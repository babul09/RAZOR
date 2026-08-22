# RAZOR — Demo Setup & Runbook

Turn-key guide to get the full RAZOR demo running locally, seed realistic data,
optionally connect live Razorpay test keys, and present the killer flow.

**Time:** ~10 minutes fresh install · ~2 minutes if already set up.

---

## 0. What you're running

| Piece | What it is | Needed for the demo? |
|-------|-----------|----------------------|
| **PostgreSQL** | Stores payments, cases, decisions, outcomes, memory | ✅ Required |
| **Redis** | Analytics cache + Celery broker | 🔸 Optional (falls back gracefully) |
| **Celery worker** | Async diagnosis/explanation tasks | 🔸 Optional — simulation runs inline now |
| **FastAPI backend** | The RAZOR API on `:8000` | ✅ Required |
| **Next.js dashboard** | The UI on `:3000` (we use `:3050`) | ✅ Required |
| **Razorpay test keys** | Live payment-link recovery + comparison | 🔸 Optional (mock fallback otherwise) |
| **Gemini key** | LLM diagnosis/explanation text | 🔸 Optional (rule-based fallback) |

---

## 1. Prerequisites

Install once:
- **Python 3.11+**
- **Node.js 18+** (we use v26)
- **PostgreSQL** running locally (role `razor` / db `razor_db`)
- **Redis** running locally (optional)

### Create the Postgres role + DB (if not already done)
```bash
psql -U postgres -c "CREATE ROLE razor WITH LOGIN PASSWORD 'razor';"
psql -U postgres -c "CREATE DATABASE razor_db OWNER razor;"
```

---

## 2. Backend setup

```bash
cd /home/kelvin/Documents/RAZOR

# Python venv + deps
python -m venv .venv && source .venv/bin/activate
pip install -e .

# Environment config
cp .env.example .env
```

### `.env` — the only file you must edit
```dotenv
DATABASE_URL=postgresql://razor:razor@localhost:5432/razor_db
REDIS_URL=redis://localhost:6379/0
GEMINI_API_KEY=              # optional
SECRET_KEY=change_me
ENVIRONMENT=development

# Razorpay test keys (optional, for the live Razorpay tab)
RAZORPAY_KEY_ID=rzp_test_xxxx
RAZORPAY_KEY_SECRET=xxxxxxxx
RAZORPAY_MOCK=true
```

### Apply migrations + seed the DB
```bash
alembic upgrade head                 # schema (incl. recovery_memory)
python scripts/seed_db.py            # idempotent 20k base dataset (optional)
```

### Populate the demo dashboard data (the important one)
The dashboard reads live from the DB — without data it looks empty. Seed a
realistic recovery run so Overview / Queue / Strategy / drill-down all show content:
```bash
python scripts/demo_data.py --events 800 --reset
```
> `--reset` clears prior recovery/payment rows so the demo is repeatable.
> `--events 800` → ~₹69L at risk, ~112 recovered, ~17% rate. Use fewer for a quicker run.

### Start the backend
```bash
uvicorn api.main:app --port 8000
```
Verify: `curl http://localhost:8000/api/analytics/overview` returns populated numbers.

---

## 3. Frontend (dashboard) setup

```bash
cd /home/kelvin/Documents/RAZOR/web
npm install
npm run dev -- -p 3050
```
Open **http://localhost:3050**.

> `NEXT_PUBLIC_API_URL` defaults to `http://localhost:8000`. If your backend is on a
> different host, set `NEXT_PUBLIC_API_URL` in `web/.env.local`.

> **Tip:** don't run `npm run build` while the dev server is running — both write to
> `.next` and can corrupt it. Stop the dev server, `rm -rf .next`, then build/run.

---

## 4. (Optional) Live Razorpay test keys

To power the **Razorpay** tab with the real test API:
1. Get keys: https://dashboard.razorpay.com → **Account → API Keys** → generate Test keys.
2. Put them in `.env` (`RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`).
3. Restart the backend.

The tab then:
- **Recover** creates a **real payment link** on the test API (`rzp.io/...`).
- Shows live failed payments **if your account has them**; otherwise it shows
  clearly-labeled **sample data** (a fresh test account has none yet).

### Seed live orders + payment links
```bash
python scripts/seed_razorpay.py            # 10 orders + 10 payment links
python scripts/seed_razorpay.py --n 5
python scripts/seed_razorpay.py --links-only
```
> Razorpay can't fabricate *failed* payments via API — those come from a checkout.
> Pay a seeded link with a **declining test card** to generate one.

---

## 5. (Optional) Async workers

Only needed for background diagnosis/explanation tasks and large simulations:
```bash
celery -A agents.celery_app worker --loglevel=info
```
The simulation endpoint now runs **synchronously inline** (no worker required), so you
can demo without Celery.

---

## 6. Verify the demo is ready

```bash
# Backend healthy?
curl -s http://localhost:8000/api/health
curl -s http://localhost:8000/api/analytics/overview      # at_risk > 0, recovered > 0

# Razorpay (if keys set)?
curl -s http://localhost:8000/api/razorpay/health         # configured:true
curl -s http://localhost:8000/api/razorpay/links          # live links

# Dashboard reachable?
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3050   # 200
```

---

## 7. The demo flow (what to click)

Full script with timing in **[WALKTHROUGH.md](./WALKTHROUGH.md)**. Quick beats:

1. **Overview** — `+₹7.22L incremental revenue`, recovery meter, ₹ at risk.
2. **Recovery Queue** — live table; **click a row** → drill-down timeline + audit trail.
3. **Razorpay** *(new)* — navy header, side-by-side baseline-vs-RAZOR comparison over
   failed payments; click **Recover** → a real Razorpay payment link is created.
4. **Strategy** — per-strategy recoveries & costs.
5. **Simulation** — hit **Run recovery simulation** → full baseline-vs-RAZOR projection
   with strategy attribution (works without Celery).

---

## 8. Troubleshooting

| Symptom | Fix |
|---------|-----|
| Dashboard empty | Run `python scripts/demo_data.py --events 800 --reset`; dashboard reads the DB. |
| `psycopg2` connection refused | Postgres not running / wrong `DATABASE_URL`. |
| Simulation stuck "Running…" | Old build — stop dev server, `rm -rf web/.next`, restart. |
| `IntegrityError` on reset | FK order handled in `demo_data.py` (policies→merchants); re-run. |
| Razorpay tab says "demo mode" | Set `RAZORPAY_KEY_ID`/`RAZORPAY_KEY_SECRET` in `.env`, restart backend. |
| CORS errors in browser | Backend already allows all origins; ensure you hit `:8000`. |
| `a[d] is not a function` in build | Dev server + `next build` conflict — kill dev server, `rm -rf .next`, rebuild. |

---

## 9. Quick reference (all commands)

```bash
# Backend
source .venv/bin/activate
alembic upgrade head
python scripts/demo_data.py --events 800 --reset
uvicorn api.main:app --port 8000

# Frontend
cd web && npm run dev -- -p 3050

# Optional
python scripts/seed_razorpay.py            # live Razorpay orders + links
celery -A agents.celery_app worker --loglevel=info
```
