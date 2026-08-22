# RAZOR — Project State

## Current Status
- **Milestone**: M2 — Agent Layer & Backend API
- **Active Phase**: Phase 4 · Diagnosis Agent (Gemini)
- **Workflow State**: EXECUTION_COMPLETE — Phase 4 implementation complete; full test suite (41) passes; Celery tasks registered on Redis broker

## Last Action
- Phase 4 implementation completed: DiagnosisAgent (FR-04 schema, gated Gemini, rule-based fallback), ExplanationAgent, Celery diagnose/explain tasks on Redis; deps clean
- Date: 2026-08-22

## Phase 4 Locked Decisions
| Decision | Choice |
|----------|--------|
| Async model | Celery + Redis now (Redis running on :6379) |
| Gemini key | Gated Gemini client + mock tests (no key in .env; rule-based fallback offline) |
| Explanation agent | Included (`agents/explanation_agent.py`) |


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
1. Run `/gsd-plan-phase 5` for the FastAPI backend (M2 continues)
2. Phase 4 note: `celery -A agents.celery_app worker` for real async; add `GEMINI_API_KEY` to `.env` to enable the live LLM path

## Simulation Target Numbers
| Metric | Baseline | RAZOR |
|--------|----------|-------|
| Revenue at risk | ₹48.2L | ₹48.2L |
| Recovered | ₹7.4L | ₹13.8L |
| Recovery rate | 15.4% | 28.6% |
| Discount cost | ₹1.2L | ₹0.38L |
| Net recovered | ₹6.2L | ₹13.42L |
| **Incremental** | — | **+₹7.22L** |
