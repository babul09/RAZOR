# Phase 7: Next.js Dashboard — Research

**Researched:** 2026-08-22
**Domain:** Next.js frontend consuming the Phase 5/6 FastAPI backend; live queue via SSE.
**Confidence:** MEDIUM (frontend build + integration).

## Locked Decisions (user-confirmed)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Location | **`web/` subfolder** | Monorepo-style, same git repo. |
| Data source | **Live backend + mock fallback** | Use Phase 5/6 API; fall back to mock when unreachable. |
| Real-time | **SSE** | Backend streams recovery-case updates; dashboard uses EventSource. |
| Deploy | **Build now, document Vercel steps** | No Vercel account confirmed; deploy steps recorded. |

## Environment (verified)

- Node v26.7.0, npm 12.0.2 available.
- Backend: FastAPI at `api/main.py` (Phase 5/6) with endpoints: `/api/recovery/cases`, `/api/recovery/cases/{id}`, `/api/analytics/overview`, `/api/analytics/strategies`, `/api/experiments`, `/api/simulation/run`, `/api/simulation/status/{job_id}`. Run via `uvicorn api.main:app`.
- **No SSE endpoint yet** → Phase 7 adds one (FastAPI `StreamingResponse` with `text/event-stream`).
- Stack per roadmap: Next.js App Router + TypeScript + Tailwind + Recharts.

## Requirements

- **FR-14** Dashboard 5 sections: Overview (₹ at risk | recovered | rate | Δ vs baseline), Live Recovery Queue (customer/amount/issue/probability/action), Agent Activity (decision timeline), Strategy Performance (attempts/recovery %/₹), Simulation (run → results).
- **AC-06** Clicking a customer shows full decision timeline + audit trail.
- Roadmap extras: policy-block visualization, real-time polling/SSE, case drill-down modal.

## Design

### Backend SSE endpoint (new)
- `GET /api/recovery/events` — `StreamingResponse` (`text/event-stream`) yielding periodic case updates (e.g., latest cases every N seconds) as `data: <json>\n\n`. Implement with a small generator; keep it simple and terminable.

### `web/` Next.js app
- Scaffold with `create-next-app` (App Router, TypeScript, Tailwind, ESLint). Add `recharts`.
- API client `web/lib/api.ts`: typed fetch wrappers; `NEXT_PUBLIC_API_URL` env with fallback to `http://localhost:8000`; on fetch failure, return mock data (mock fallback).
- Layout with sidebar/tabs for the 5 sections.
- Components:
  - `OverviewSection` — Recharts (bar/line) + stat cards from `/api/analytics/overview`.
  - `RecoveryQueueSection` — table from `/api/recovery/cases`; subscribes to SSE `/api/recovery/events` for live updates; action badges.
  - `AgentActivitySection` — timeline from `/api/recovery/cases/{id}` decision timeline.
  - `StrategyPerformanceSection` — table from `/api/analytics/strategies`.
  - `SimulationSection` — run button → POST `/api/simulation/run` → poll status → results comparison.
  - `CaseDrillDown` — modal showing full decision timeline + audit trail (AC-06), incl. policy-block rows.
- `web/README.md` — run + Vercel deploy steps.

## Risk / mitigation
- **Backend down** → mock fallback keeps UI usable.
- **SSE** → simple StreamingResponse; client reconnects EventSource.
- **Build size/time** → scaffold then implement sections incrementally; build with `next build`.
- **Deploy** → document Vercel steps; no live deploy this phase.
