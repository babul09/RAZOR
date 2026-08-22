# RAZOR — Revenue AI Zero-loss Operations and Recovery

> **AI decides. ML predicts. Rules protect. APIs execute. Data proves.**

## Project Overview

RAZOR is a **closed-loop Revenue Recovery Agent** for payment businesses. It monitors every payment failure and lost-revenue event, then autonomously diagnoses, predicts, decides, and executes recovery actions — all within a controlled policy guardrail framework.

The system is designed as a hackathon submission targeting Indian payment infrastructure (Razorpay ecosystem). The differentiator is **"Recovery Brain"** — a multi-layer intelligence stack that is both autonomous *and* auditable.

## Vision

Transform payment failures from accepted losses into recoverable revenue, using a self-optimizing agent that gets smarter with every case it resolves.

## Core Philosophy

```
Ingest → Detect → Diagnose → Predict → Decide → Guardrail → Execute → Verify → Learn
```

| Layer | Technology |
|-------|-----------|
| Prediction | ML / XGBoost / scikit-learn |
| Safety | Rule engine / policy YAML |
| Diagnosis & Strategy | LLM (Gemini Pro / Flash) |
| Money calculations | Deterministic Python |
| Execution | Event-driven workflows |

## Target Users

| User | Context |
|------|---------|
| **Merchant / Finance team** | Sees recovery dashboard, approves high-value escalations |
| **Judges / Demo audience** | Runs the simulation and watches ₹ recovered vs baseline |
| **System (autonomous)** | Handles sub-₹5,000 cases automatically within policy |

## Key Metrics

### Primary
- **Incremental Revenue Recovered** (₹ vs baseline)

### Secondary
- Recovery Rate (%)
- Net Revenue Recovered (after recovery cost)
- Cost per Recovery
- False Intervention Rate
- Customer Contact Rate
- Average Recovery Time
- Human Escalation Rate

## Tech Stack

| Layer | Choice |
|-------|--------|
| Frontend | Next.js + React + Tailwind |
| Backend | Python + FastAPI |
| Database | PostgreSQL |
| Queue | Redis + Celery |
| ML | pandas + scikit-learn + XGBoost |
| LLM | Google Gemini (Pro / Flash) |
| Charts | Recharts / ECharts |
| Frontend deploy | Vercel |
| Backend deploy | Railway / Render |
| DB deploy | Managed PostgreSQL |

## Currency
Primary currency: **₹ INR**

## Team
Solo build — hackathon timeframe.

## Domain Context

### Payment Failure Categories
- `INSUFFICIENT_FUNDS` — temporary liquidity issue
- `CARD_DECLINED` — bank-level block
- `UPI_FAILURE` — technical/timeout
- `AUTHENTICATION_FAILED` — 3DS / OTP issue
- `NETWORK_ERROR` — connectivity
- `FRAUD_SUSPECTED` — risk block

### Recovery Strategies
| Strategy | Mechanism |
|----------|-----------|
| `RETRY` | Automated payment retry at optimal time |
| `PAYMENT_METHOD_SWITCH` | Suggest UPI / card / netbanking alternative |
| `WHATSAPP_REMINDER` | Conversational nudge via WhatsApp |
| `EMAIL_REMINDER` | Scheduled email with payment link |
| `PAYMENT_LINK` | Fresh checkout link generation |
| `DISCOUNT_OFFER` | Incentive (guardrailed by policy) |
| `HUMAN_ESCALATION` | Hand off to customer success team |
| `WAIT` | Delay action — higher expected value later |
| `STOP` | Recovery cost exceeds expected value; abandon |

### Policy Guardrails (Example Merchant Policy)
```yaml
max_discount_percent: 10
max_automated_transaction_value: 5000
max_customer_contacts:
  count: 3
  window_days: 7
require_human_approval_above: 5000
allowed_channels:
  - whatsapp
  - email
stop_if_payment_succeeds: true
```

## Core Data Model (Key Tables)

```
merchants | customers | payments | payment_attempts
subscriptions | invoices | recovery_cases
customer_recovery_profiles | recovery_actions
agent_decisions | recovery_outcomes | experiments
policies | audit_logs
```

## Architecture

```
Ingest → Risk Engine → Diagnosis Agent (Gemini) → Recovery Predictor (ML)
→ Strategy Engine → Policy/Guardrail → [Auto Action | Human Review]
→ Outcome Verifier → Learning / Analytics
```

## Backend Service Structure

```
backend/
├── api/           # FastAPI routes: payments, recovery, simulation, analytics
├── agents/        # diagnosis_agent, strategy_agent, explanation_agent
├── ml/            # recovery_model, feature_engineering, training
├── engine/        # risk_engine, decision_engine, policy_engine, state_machine
├── integrations/  # payment_adapter, notification_adapter, webhook_adapter
├── simulation/    # generator, simulator, evaluator
└── db/            # models, repository
```

## Dashboard Sections (5)
1. **Overview** — ₹ at risk, ₹ recovered, recovery rate vs baseline
2. **Live Recovery Queue** — customer | amount | issue | probability | action
3. **Agent Activity** — decision timeline
4. **Strategy Performance** — per-strategy recovery rate and revenue
5. **Simulation** — run 10,000 events, see ₹ recovered vs baseline

## Killer Demo Moment

> **Run simulation → ₹48.2L at risk → ₹13.8L recovered vs ₹7.4L baseline → +₹7.22L incremental**

Then drill into one customer's full decision timeline.

## Project Status
- Phase: **Initialization**
- Milestone: **M1 — Foundation & Core Engine**
