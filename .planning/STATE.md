# RAZOR — Project State

## Current Status
- **Milestone**: M4 — Polish, Demo & Submission
- **Active Phase**: Phase 8 · Demo Hardening & Integration Tests
- **Workflow State**: EXECUTION_COMPLETE — Phase 8 implementation complete; full test suite (69) passes; E2E integration + 10-step demo flow verified; web builds

## Last Action
- Phase 8 implementation completed: standardized API errors, E2E integration test, 10-step demo-flow pytest, dashboard loading/empty states
- Date: 2026-08-22

## Phase 8 Locked Decisions
| Decision | Choice |
|----------|--------|
| Demo validation | pytest-based (10-step demo flow) |
| Integration test | Live DB + Redis (eager simulation) |
| Error handling | Standardize error shape across API |
| UI states | Add loading + empty states to all sections |


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
1. Run `/gsd-plan-phase 9` for Polish & Submission (final M4 phase)
2. Phase 8 note: `python -m pytest tests/test_demo_flow.py` validates the full demo flow

## Simulation Target Numbers
| Metric | Baseline | RAZOR |
|--------|----------|-------|
| Revenue at risk | ₹48.2L | ₹48.2L |
| Recovered | ₹7.4L | ₹13.8L |
| Recovery rate | 15.4% | 28.6% |
| Discount cost | ₹1.2L | ₹0.38L |
| Net recovered | ₹6.2L | ₹13.42L |
| **Incremental** | — | **+₹7.22L** |
