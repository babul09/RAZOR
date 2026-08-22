# RAZOR — Project State

## Current Status
- **Milestone**: M4 — Polish, Demo & Submission
- **Active Phase**: Phase 9 · Polish & Submission
- **Workflow State**: EXECUTION_COMPLETE — Phase 9 implementation complete; full test suite (69) passes; dashboard polished with +₹7.22L headline; README + deploy/submission/walkthrough docs done

## Last Action
- Phase 9 implementation completed: design-token UI polish + INR + headline, full README with Mermaid diagram, deploy guide, submission checklist, walkthrough script
- Date: 2026-08-22

## Phase 9 Locked Decisions
| Decision | Choice |
|----------|--------|
| Deployment | Docs-only deploy guide (Vercel + Railway + managed Postgres) |
| UI polish | Design-token pass + INR + prominent +₹7.22L headline |
| README + diagram | Full root README + Mermaid architecture diagram |
| Video | Document 2-3 min walkthrough script (manual) |


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
1. Manual items (docs ready): live Vercel/Railway deploy (`docs/DEPLOYMENT.md`), record demo video (`docs/WALKTHROUGH.md`), finalize submission (`docs/SUBMISSION.md`)
2. **All roadmap phases 1-9 complete** — full suite 69 tests pass, dashboard polished, docs/submission package delivered

## Simulation Target Numbers
| Metric | Baseline | RAZOR |
|--------|----------|-------|
| Revenue at risk | ₹48.2L | ₹48.2L |
| Recovered | ₹7.4L | ₹13.8L |
| Recovery rate | 15.4% | 28.6% |
| Discount cost | ₹1.2L | ₹0.38L |
| Net recovered | ₹6.2L | ₹13.42L |
| **Incremental** | — | **+₹7.22L** |
