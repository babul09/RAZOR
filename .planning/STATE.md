# RAZOR — Project State

## Current Status
- **Milestone**: M1 — Foundation & Core Intelligence
- **Active Phase**: Phase 1 · Data & Simulation Foundation
- **Workflow State**: EXECUTION_COMPLETE — Phase 1 implementation complete; database verification pending PostgreSQL

## Last Action
- Phase 1 implementation completed: data generator, simulators, evaluator, CLI, seed script, and README
- Date: 2026-08-22

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
1. Start PostgreSQL and run `alembic upgrade head`
2. Run `python scripts/seed_db.py` twice to verify idempotency
3. Run `/gsd-plan-phase 2` for the ML recovery prediction model

## Simulation Target Numbers
| Metric | Baseline | RAZOR |
|--------|----------|-------|
| Revenue at risk | ₹48.2L | ₹48.2L |
| Recovered | ₹7.4L | ₹13.8L |
| Recovery rate | 15.4% | 28.6% |
| Discount cost | ₹1.2L | ₹0.38L |
| Net recovered | ₹6.2L | ₹13.42L |
| **Incremental** | — | **+₹7.22L** |
