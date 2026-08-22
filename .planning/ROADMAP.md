# RAZOR — Roadmap

> Build order: simulation + decision engine must produce convincing ₹ recovered vs baseline **before** the UI.
> Consolidated into 4 milestones, each with sub-phases.

---

## M1 — Foundation & Core Intelligence

> **Goal**: End-to-end pipeline working in Python scripts. No UI needed. The simulation produces ₹ recovered vs baseline.

### Phase 1 · Data & Simulation Foundation
**Objective**: Synthetic dataset + simulator backbone
- [ ] Define all DB models (SQLAlchemy + PostgreSQL schema)
- [ ] Build synthetic event generator (20,000 events, 5 behavioral segments)
- [ ] Build baseline simulator (dumb retry logic, ~15.4% recovery rate)
- [ ] Build RAZOR simulator (pluggable strategy engine, runs on generated data)
- [ ] Write simulation evaluator (outputs comparison table with ₹ metrics)
- [ ] Seed DB with generated dataset

**Deliverable**: `python simulate.py` outputs ₹ recovered vs baseline table

---

### Phase 2 · ML Recovery Prediction Model
**Objective**: Trained model that outputs P(recovery | strategy)
- [x] Feature engineering pipeline (12 features from requirements)
- [x] Train logistic regression baseline model
- [x] Train XGBoost model; compare vs baseline
- [x] Per-strategy probability output: RETRY, METHOD_SWITCH, WHATSAPP, EMAIL, DISCOUNT
- [x] Model persistence (joblib / pickle)
- [x] Unit tests: model outputs valid probabilities for all strategy types

**Deliverable**: `ml/recovery_model.py` with `.predict_proba(features, strategy)` API

---

### Phase 3 · Decision Engine & Policy Guardrails
**Objective**: Strategy engine + policy enforcement
- [x] Strategy engine: expected net recovery calculation per strategy
- [x] WAIT strategy: compares now vs N-hours-later expected value
- [x] STOP strategy: abandons if max(expected_net) < 0
- [x] Policy engine: loads merchant YAML config, enforces all 7 policy checks
- [x] Audit log: every decision writes to `agent_decisions` + `audit_logs`
- [x] Recovery state machine: all 12 states, deterministic transitions
- [x] Demo: policy blocks discount offer; agent chooses WAIT over immediate retry

**Deliverable**: `engine/decision_engine.py` + `engine/policy_engine.py` + `engine/state_machine.py`

---

## M2 — Agent Layer & Backend API

> **Goal**: Gemini-powered Diagnosis Agent live. FastAPI serving recovery cases and decisions.

### Phase 4 · Diagnosis Agent (Gemini)
**Objective**: LLM diagnosis with structured output
- [x] Google Gemini API integration (gemini-pro for diagnosis, gemini-flash for explanations)
- [x] Prompt engineering: patient history + failure context → structured JSON diagnosis
- [x] Output schema: `{ diagnosis, confidence, recommended_timing, reason, avoid_discount }`
- [x] Explanation agent: generates human-readable decision explanation for dashboard
- [x] Async: LLM calls are non-blocking (Celery task)
- [x] Fallback: if LLM unavailable, use rule-based diagnosis

**Deliverable**: `agents/diagnosis_agent.py` with async `.diagnose(case)` API

---

### Phase 5 · FastAPI Backend
**Objective**: REST API serving all frontend needs
- [x] `GET /api/recovery/cases` — paginated recovery queue
- [x] `GET /api/recovery/cases/{id}` — case detail + decision timeline
- [x] `POST /api/simulation/run` — trigger simulation with N events
- [x] `GET /api/analytics/overview` — ₹ at risk, recovered, recovery rate
- [x] `GET /api/analytics/strategies` — per-strategy performance table
- [x] `GET /api/experiments` — A/B experiment results
- [x] `POST /api/events/ingest` — webhook endpoint for events
- [x] Celery workers: async diagnosis + action execution
- [x] Redis: task queue + caching for dashboard metrics

**Deliverable**: Backend serving all API endpoints, Celery workers running

---

## M3 — Dashboard & Experiment Engine

> **Goal**: Full dashboard live. Experiment engine wired. Demo-ready.

### Phase 6 · Recovery Memory + Experiment Engine
**Objective**: Learning loop + A/B experiments
- [x] Recovery memory: `(customer, failure_type, strategy, outcome)` stored after each case
- [x] Customer profile update: per-channel success rates recomputed after each case
- [x] Experiment engine: traffic allocation (control / retry / whatsapp / UPI switch)
- [x] Per-arm metrics: recovery rate, revenue, cost, net revenue
- [x] Strategy weight update from experiment results
- [x] Display experiments in API response

**Deliverable**: `engine/experiment_engine.py`, customer profile auto-updates

---

### Phase 7 · Next.js Dashboard
**Objective**: 5-section dashboard, simulation UI, case drill-down
- [x] **Overview section**: ₹ at risk | ₹ recovered | recovery rate | Δ vs baseline (Recharts)
- [x] **Live Recovery Queue**: table with customer, amount, issue, probability, action badges
- [x] **Agent Activity**: timeline component with diagnosis + decision reasoning per case
- [x] **Strategy Performance**: table — attempts | recovery % | ₹ recovered
- [x] **Simulation section**: "Run Recovery Simulation" button → progress → results table
- [x] Case drill-down: full decision timeline + audit trail modal
- [x] Policy block visualization: show guardrail trigger in timeline
- [x] Real-time polling (or SSE) for live queue updates

**Deliverable**: Dashboard deployed to Vercel, all 5 sections working

---

## M4 — Polish, Demo & Submission

> **Goal**: Flawless demo flow. Pitch deck moment captured. Submission ready.

### Phase 8 · Demo Hardening & Integration Tests
**Objective**: End-to-end integration + demo script validation
- [ ] End-to-end test: ingest 10,000 events → simulation → dashboard shows results
- [ ] Demo script: validate all 10 steps of the "killer demo flow"
  - Step 1: Generate 10,000 events
  - Step 2: System shows ₹48.2L at risk
  - Step 3: Agent diagnoses failure categories
  - Step 4: System shows ₹19.4L potentially recoverable
  - Step 5: Strategy action breakdown shown
  - Step 6: Simulation runs
  - Step 7: ₹13.8L recovered vs ₹7.4L baseline
  - Step 8: Customer drill-down with decision timeline
  - Step 9: Policy engine blocking demo
  - Step 10: Learning loop demonstration
- [ ] Error handling: all API routes return structured errors
- [ ] Loading states, empty states in UI

---

### Phase 9 · Polish & Submission
**Objective**: Pitch-ready final state
- [ ] UI visual polish (consistent INR formatting, color system, typography)
- [ ] Dashboard headline: `+₹7.22L incremental revenue` prominently displayed
- [ ] README.md: setup instructions, architecture diagram, demo steps
- [ ] Architecture diagram in pitch-friendly format
- [ ] Deployment: Vercel (frontend) + Railway (backend) + managed PostgreSQL
- [ ] Record demo video (2-3 min walkthrough of all 10 demo steps)
- [ ] Final submission package

---

## Build Principles

1. **Simulation + decision engine before UI** — if the ₹ numbers aren't convincing, nothing else matters
2. **LLM only for diagnosis and reasoning** — never in payment execution path
3. **Policy engine is a hard gate** — always runs before any action
4. **Every decision is logged** — full audit trail from day one
5. **WAIT and STOP are first-class strategies** — AI not taking action is a feature, not a bug
