# Plan 07-01 Summary — Next.js Scaffold + SSE + Overview/Live Queue

**Phase:** 07-nextjs-dashboard · **Plan:** 01 · **Wave:** 1
**Status:** COMPLETE

## What was built

- **Backend SSE** — `GET /api/recovery/events` in `api/routers/recovery.py` (FastAPI `StreamingResponse`, `text/event-stream`, streams latest 50 cases every 3s). **CORS middleware** added to `api/main.py` (allow all, demo) so the browser dashboard can call the API.
- **`web/` Next.js app** — App Router, TypeScript, Tailwind, Recharts. `package.json`, `next.config.mjs`, `tsconfig.json`, `tailwind.config.ts`, `postcss.config.mjs`, `app/layout.tsx`, `app/globals.css`, `app/page.tsx`.
- **`web/lib/api.ts`** — typed API client (`NEXT_PUBLIC_API_URL`, default `http://localhost:8000`) with mock fallback; `formatInr` (₹, integer paise).
- **`web/lib/mock.ts`** — mock fallback data.
- **`web/components/OverviewSection.tsx`** — stat cards + Recharts bar chart from `/api/analytics/overview`.
- **`web/components/RecoveryQueueSection.tsx`** — live queue table via `/api/recovery/cases` + `EventSource` SSE (fallback to polling on error).

## Verification
- `npm run build` → **OK**.
- `curl` SSE → streams `data: [...]` JSON.
- Browser: Overview renders live data (₹34,780 at risk from DB), Live Queue renders live cases via SSE, no CORS error after middleware.

## Notes
- CORS was required for the browser→API path (fell back to mock otherwise); fixed with middleware.
