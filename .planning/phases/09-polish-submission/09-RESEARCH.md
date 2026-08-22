# Phase 9: Polish & Submission — Research

**Researched:** 2026-08-22
**Domain:** Final polish, docs, architecture diagram, deploy guide, and submission package.
**Confidence:** HIGH.

## Locked Decisions (user-confirmed)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Deployment | **Docs-only deploy guide** | Vercel frontend + Railway backend + managed Postgres; no live deploy (accounts needed). |
| UI polish | **Design-token pass + headline** | Consistent INR formatting, color system, typography; prominent `+₹7.22L incremental` on Overview. |
| README + diagram | **Full root README + Mermaid diagram** | Setup, architecture, demo steps, deploy guide. |
| Video | **Document walkthrough script** | 2-3 min demo script as a manual submission item. |

## Environment (verified)

- Full stack complete (Phases 1-8): simulation, ML, decision/policy/state engine, agents, FastAPI backend (SSE + CORS + structured errors), Next.js dashboard. 69 backend tests pass; web builds.
- `web/README.md` has basic run + Vercel steps.
- Deployment targets: Vercel (frontend), Railway (backend), managed PostgreSQL.

## Requirements

- Dashboard headline `+₹7.22L incremental revenue` prominent (ROADMAP Phase 9).
- README: setup instructions, architecture diagram, demo steps (ROADMAP Phase 9).
- Deployment: Vercel + Railway + managed PostgreSQL (ROADMAP Phase 9).
- Record demo video (manual) — provide script/checklist.
- Final submission package.

## Design

### UI polish (`web/`)
- Design tokens: INR formatting already via `formatInr`; enforce consistent ₹ display; align color/typography via Tailwind config (brand palette, consistent spacing/type scale).
- Overview: add a prominent `+₹7.22L incremental revenue` headline band (from simulation comparison), styled.
- Build must stay green.

### Docs
- `README.md` (root): project intro, architecture, setup (Postgres/Redis, migrations, backend, dashboard), demo steps, deploy guide (Vercel/Railway/managed Postgres), tech stack.
- Mermaid architecture diagram embedded in README (generator -> simulators -> ML -> decision/policy/state engine -> agents -> FastAPI -> Next.js dashboard; Postgres + Redis + Celery).
- `docs/DEPLOYMENT.md` — detailed Vercel + Railway + managed Postgres steps.
- `docs/SUBMISSION.md` — submission checklist (build, tests, demo steps, video, deploy).
- `docs/WALKTHROUGH.md` — 2-3 min demo video script walking the 10 steps.

## Risk / mitigation
- **No live deploy/video** → docs cover them as manual steps; everything else is deliverable now.
- **README accuracy** → verify commands/endpoints against the codebase.
- **UI polish regression** → `npm run build` gate.
