# RAZOR — Requirements

> Hackathon MVP. Solo build. Priority: working demo with ₹ recovered vs baseline as the headline metric.

---

## 1. Functional Requirements

### FR-01 · Event Ingestion
- System accepts payment/business events via REST API and/or webhook
- Supported event types: `payment.failed`, `payment.success`, `checkout.abandoned`, `invoice.overdue`, `subscription.failed`, `refund.created`, `dispute.created`
- Events must be idempotent (duplicate events do not create duplicate cases)
- **Hackathon path:** Synthetic event generator replaces real production webhooks

### FR-02 · Revenue Risk Engine
- On each `payment.failed` event, auto-create a `recovery_case`
- Calculate a **Revenue Risk Score** = `transaction_value × failure_severity × recovery_probability × customer_value_factor`
- Cases are prioritized by risk score; ₹50 failures don't block ₹50,000 failures

### FR-03 · Customer Recovery Profile
- Maintain a dynamic profile per customer:
  - Lifetime value, preferred payment method, typical payment time window
  - Per-channel historical recovery rates (WhatsApp, email, retry, UPI switch)
  - Running recovery probability score
- Profile must update after every resolved case

### FR-04 · Diagnosis Agent (LLM)
- Uses Gemini Pro/Flash to reason about *why* a failure occurred
- Input: payment data + customer profile + historical context
- Output: `{ diagnosis, confidence, recommended_timing, reason, avoid_discount }`
- **The LLM must not directly execute any payment action**

### FR-05 · Recovery Prediction Model (ML)
- Trained on synthetic dataset (20,000 events with deliberate behavioral patterns)
- Features: transaction_amount, payment_method, failure_code, customer_ltv, previous_successes, previous_failures, time_since_last_payment, historical_payment_hour, historical_payment_day, previous_strategy, previous_strategy_success_rate
- Output: `P(recovery | strategy)` for each available strategy
- Acceptable models: logistic regression, gradient-boosted tree (XGBoost preferred)

### FR-06 · Strategy Engine
- Evaluates all candidate strategies using: `expected_net_recovery = P(recovery) × amount - cost`
- Strategies evaluated: RETRY, PAYMENT_METHOD_SWITCH, WHATSAPP_REMINDER, EMAIL_REMINDER, PAYMENT_LINK, DISCOUNT_OFFER, HUMAN_ESCALATION, WAIT, STOP
- **Explicit WAIT strategy**: if expected recovery is higher in N hours, output WAIT with timestamp
- **Explicit STOP strategy**: if `max(expected_net_recovery) < 0` across all strategies, output STOP
- Decision is logged to `agent_decisions` table with full reasoning

### FR-07 · Policy / Guardrail Engine
- Each merchant has a policy YAML/config loaded at runtime
- Policy checks run **before every action** (hard gate)
- Policy attributes: `max_discount_percent`, `max_automated_transaction_value`, `max_customer_contacts.count`, `max_customer_contacts.window_days`, `require_human_approval_above`, `allowed_channels`, `stop_if_payment_succeeds`
- On policy block: route to human review queue; log block reason to `audit_logs`
- **This is the safety layer; no exceptions**

### FR-08 · Action Executor (Adapters)
- Adapters (simulator-backed for hackathon, real-API-compatible):
  - `PaymentAdapter.retry(payment_id)`
  - `NotificationAdapter.send_whatsapp(customer_id, template_id)`
  - `NotificationAdapter.send_email(customer_id, template_id)`
  - `PaymentAdapter.generate_payment_link(payment_id)`
- All actions write to `recovery_actions` table

### FR-09 · Recovery State Machine
- Each `recovery_case` progresses through:
  `NEW → DIAGNOSING → PREDICTED → STRATEGY_SELECTED → POLICY_CHECK → AWAITING_APPROVAL → EXECUTING → VERIFYING → [RECOVERED | FAILED → NEXT_STRATEGY → STOPPED]`
- State transitions are deterministic and logged
- Failed strategy → next best strategy attempted (up to policy-allowed contact limit)

### FR-10 · Outcome Verifier
- After action execution, poll/webhook for outcome: payment success, click, response, method change
- Record: `recovery_rate`, `revenue_recovered`, `cost_of_recovery`, `net_revenue_recovered`
- Write to `recovery_outcomes` table

### FR-11 · Recovery Memory (Learning Loop)
- After each resolved case: store `(customer, failure_type, strategy, outcome)` tuple
- Customer profile updates its per-channel success rates
- Next case for same customer uses updated probabilities

### FR-12 · A/B Experiment Engine
- Ability to define experiments: allocate % of similar failures to control vs treatment strategies
- Track per-arm: recovery rate, revenue, cost, net revenue
- System updates strategy weights based on experiment results
- **Claim**: "Self-optimizing recovery" (backed by experiment data)

### FR-13 · Simulation Engine
- Generate N synthetic failed revenue events (default: 10,000 for demo)
- Run baseline (no recovery system) — baseline rate ≈ 15.4%
- Run RAZOR — system applies full pipeline
- Output comparison table:
  ```
                      BASELINE    RAZOR
  Revenue at risk      ₹48.2L     ₹48.2L
  Recovered            ₹7.4L      ₹13.8L
  Recovery rate        15.4%      28.6%
  Interventions        8,200      5,940
  Discount cost        ₹1.2L      ₹0.38L
  Net recovered        ₹6.2L      ₹13.42L
  ```
- **This is the demo's hero moment**

### FR-14 · Dashboard
- **5 sections:**
  1. Overview: ₹ at risk | ₹ recovered | recovery rate | Δ vs baseline
  2. Live Recovery Queue: customer | amount | issue | probability | recommended action
  3. Agent Activity: decision timeline with reasoning per case
  4. Strategy Performance: table of attempts | recovery % | ₹ recovered per strategy
  5. Simulation: run button → results comparison
- Drill-down: click customer → full decision timeline + audit trail

---

## 2. Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-01 | API response time < 500ms for dashboard queries |
| NFR-02 | Simulation of 10,000 events completes in < 60 seconds |
| NFR-03 | All money arithmetic uses integer paise (no floating point) |
| NFR-04 | Every agent decision is logged with timestamp, inputs, outputs, policy check result |
| NFR-05 | The LLM is never in the critical path for money calculation or payment execution |
| NFR-06 | System works fully offline (simulator mode) with no real payment APIs required |
| NFR-07 | Policy engine must block before execute — no action bypasses policy check |

---

## 3. Synthetic Dataset Requirements

- **Size**: 20,000 events for training; 10,000 for demo simulation
- **Behavioral segments** (deliberate patterns for ML to learn):
  - **Segment A** (25%): Recovers after retry — `INSUFFICIENT_FUNDS` + evening payment pattern
  - **Segment B** (20%): Responds to UPI switch — recurring `UPI_FAILURE`
  - **Segment C** (20%): Responds to WhatsApp reminder — `CHECKOUT_ABANDONED`
  - **Segment D** (15%): Needs human intervention — high LTV, complex failure
  - **Segment E** (20%): Should be abandoned — low LTV + high recovery cost
- Customer features: `customer_id`, `transaction_amount`, `payment_method`, `timestamp`, `failure_code`, `failure_category`, `customer_ltv`, `previous_successes`, `previous_failures`, `previous_recovery_actions`, `previous_recovery_results`, `subscription_age`, `days_since_last_payment`, `customer_segment`

---

## 4. Out of Scope (Hackathon MVP)

- Real payment gateway integration (Razorpay production API)
- Real WhatsApp / SMS / email delivery
- Multi-tenant merchant onboarding flow
- GDPR / data privacy compliance
- Production security hardening
- Mobile app

---

## 5. Acceptance Criteria

| ID | Criteria |
|----|----------|
| AC-01 | Simulation runs end-to-end and produces ₹ recovered > baseline |
| AC-02 | Diagnosis agent outputs structured JSON reasoning for any failure |
| AC-03 | ML model outputs per-strategy recovery probability for any input |
| AC-04 | Strategy engine correctly selects WAIT when future expected value > now |
| AC-05 | Policy engine blocks a discount offer that exceeds merchant's max_discount_percent |
| AC-06 | Clicking one customer on the dashboard shows full decision timeline |
| AC-07 | Experiment engine shows per-arm recovery rate differences |
| AC-08 | All agent decisions are logged with reasons in audit_logs |
