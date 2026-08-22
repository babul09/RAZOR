# Plan 07-02 Summary — Remaining Sections + Drill-down + Docs

**Phase:** 07-nextjs-dashboard · **Plan:** 02 · **Wave:** 2
**Status:** COMPLETE

## What was built

- **`web/components/StrategyPerformanceSection.tsx`** — attempts / recovery % / ₹ recovered / cost from `/api/analytics/strategies`.
- **`web/components/SimulationSection.tsx`** — Run Simulation button → `POST /api/simulation/run` → poll `GET /api/simulation/status/{job_id}` → baseline vs RAZOR comparison + incremental ₹.
- **`web/components/AgentActivitySection.tsx`** (referenced by page; renders decision timeline from case detail).
- **`web/components/CaseDrillDown.tsx`** — modal on queue-row click: full decision timeline + audit trail, policy-block/guardrail rows highlighted (AC-06).
- **`web/lib/api.ts`** — added `getStrategies`, `runSimulation`, `getSimulationStatus`, `getCaseDetail` (mock fallback).
- **`web/app/page.tsx`** — all 5 sections wired + tabs + drill-down modal.
- **`web/README.md`** — local run + Vercel deploy steps (root dir `web`, `NEXT_PUBLIC_API_URL`).

## Verification
- `npm run build` → **OK** (final build re-confirmed).
- Backend suite → **65 passed**.
- Browser: Overview (live data + Recharts), Live Queue (SSE), Strategy (live), Simulation (renders), drill-down modal opens with timeline + audit trail.

## Notes
- Strategy/Agent sections show empty rows when the DB has no corresponding data (correct live behavior; mock fills in when API is down).
