# RAZOR — Project State

## Current Status
- **Milestone**: M3 — Dashboard & Experiment Engine
- **Active Phase**: Phase 6 · Recovery Memory + Experiment Engine
- **Workflow State**: EXECUTION_COMPLETE — Phase 6 implementation complete; full test suite (65) passes; migration 002 applied; demo experiment seeded

## Last Action
- Phase 6 implementation completed: recovery_memory table + profile recompute (Celery), weighted DecisionEngine EV, experiment engine (create/allocate/metrics/weights) + experiments API + seed script
- Date: 2026-08-22

## Phase 6 Locked Decisions
| Decision | Choice |
|----------|--------|
| Memory store | New `recovery_memory` table + alembic migration 002 (applied) |
| Profile update | Celery `update_profile` task |
| Strategy weights | EV multiplier in DecisionEngine (fed by experiments) |
| Experiment setup | POST /api/experiments (runtime creation) |


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
1. Run `/gsd-plan-phase 7` for the Next.js Dashboard (M3 continues)
2. Phase 6 note: `python scripts/seed_experiment.py` creates the demo experiment (idempotent)

## Simulation Target Numbers
| Metric | Baseline | RAZOR |
|--------|----------|-------|
| Revenue at risk | ₹48.2L | ₹48.2L |
| Recovered | ₹7.4L | ₹13.8L |
| Recovery rate | 15.4% | 28.6% |
| Discount cost | ₹1.2L | ₹0.38L |
| Net recovered | ₹6.2L | ₹13.42L |
| **Incremental** | — | **+₹7.22L** |
