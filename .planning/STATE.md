# RAZOR — Project State

## Current Status
- **Milestone**: M3 — Dashboard & Experiment Engine
- **Active Phase**: Phase 7 · Next.js Dashboard
- **Workflow State**: EXECUTION_COMPLETE — Phase 7 implementation complete; dashboard builds + renders all 5 sections, SSE + drill-down verified in browser

## Last Action
- Phase 7 implementation completed: Next.js dashboard under web/ (Overview Recharts, Live Queue SSE, Agent Activity, Strategy Performance, Simulation, case drill-down), backend SSE endpoint + CORS; build OK, browser-verified
- Date: 2026-08-22

## Phase 7 Locked Decisions
| Decision | Choice |
|----------|--------|
| Location | `web/` subfolder (App Router, TS, Tailwind, Recharts) |
| Data source | Live FastAPI backend + mock fallback |
| Real-time | SSE (GET /api/recovery/events added) |
| Deploy | Build now, document Vercel steps (web/README.md) |


## Phase 3 Locked Decisions
| Decision | Choice |
|----------|--------|
| Audit log storage | Direct PostgreSQL writes (role `razor` / `razor_db` running, migrated) |
| Outcome verifier (FR-10) | Included in Phase 3 |
| WAIT timing | Configurable per-merchant window (policy YAML) |
| Demo delivery | Seed DB + CLI (`scripts/demo_decision_engine.py`) |

## Key Decisions Made
| Decision | Choice | Rationale |
|----------|--------|-----------|
| Project name | RAZOR | Revenue AI Zero-loss Operations and Recovery — memorable acronym |
| LLM provider | Google Gemini Pro/Flash | Hackathon context, API availability |
| ML approach | XGBoost + scikit-learn | Sufficient for pattern discovery; sophistication is in decision system |
| Roadmap structure | 4 milestones (vs 9 separate phases) | Consolidated for solo build |
| Currency | ₹ INR | Indian hackathon audience |
| A/B experiments | Included in MVP | "Self-optimizing" is the key differentiator claim |
| Deployment | Vercel + Railway + managed PostgreSQL | Fast, free-tier friendly |

## Architecture Decisions
- LLM is NEVER in payment execution path
- Policy engine is a HARD GATE — always runs before action
- WAIT and STOP are first-class strategies (not failure modes)
- All money in integer paise (no floating point)
- Every agent decision logged to audit_logs

## Next Steps
1. Run `/gsd-plan-phase 8` for Demo Hardening & Integration Tests (M4 begins)
2. Phase 7 note: run backend `uvicorn api.main:app` + dashboard `cd web && npm run dev`; deploy steps in web/README.md

## Simulation Target Numbers
| Metric | Baseline | RAZOR |
|--------|----------|-------|
| Revenue at risk | ₹48.2L | ₹48.2L |
| Recovered | ₹7.4L | ₹13.8L |
| Recovery rate | 15.4% | 28.6% |
| Discount cost | ₹1.2L | ₹0.38L |
| Net recovered | ₹6.2L | ₹13.42L |
| **Incremental** | — | **+₹7.22L** |
