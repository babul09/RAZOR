# RAZOR Dashboard (web/)

Next.js dashboard for the RAZOR revenue-recovery backend.

## Run locally

Prereq: FastAPI backend running (see repo root). Default API URL is
`http://localhost:8000` (override with `NEXT_PUBLIC_API_URL`).

```bash
# 1. Start the backend (from repo root)
source .venv/bin/activate
uvicorn api.main:app --reload --port 8000

# 2. Run the dashboard
cd web
npm install
npm run dev        # http://localhost:3000
```

Sections: Overview (Recharts), Live Recovery Queue (SSE), Agent Activity,
Strategy Performance, Simulation, and case drill-down (timeline + audit trail).

If the backend is unreachable, the dashboard falls back to mock data
(`web/lib/mock.ts`).

## Build

```bash
cd web
npm run build
npm run start
```

## Deploy to Vercel

1. Push the repo to GitHub.
2. On Vercel: **Import Project** → select the repo.
3. Root Directory: `web`.
4. Add environment variable `NEXT_PUBLIC_API_URL` pointing at the deployed
   backend (e.g. the Railway-hosted FastAPI URL).
5. Deploy. The build framework is auto-detected (Next.js).
