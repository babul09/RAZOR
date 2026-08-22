# Demo Walkthrough Script (2-3 min)

Record a screen video walking the 10-step killer-demo flow. Recommended flow below with
rough time targets.

## Setup (pre-record)
- Start backend (`uvicorn api.main:app`) and dashboard (`cd web && npm run dev`).
- Ensure PostgreSQL + Redis are running and seeded.

## Script

**0:00 — Hook**
> "This is RAZOR — an AI recovery engine that turns failed payments into recovered revenue.
> Here's the full closed loop, live."

**0:05 — Step 1–2: Generate events & ₹ at risk**
> Open the dashboard Overview. "We generate 10,000 synthetic payment failures. RAZOR shows
> the revenue at risk up front — the recovery opportunity."

**0:25 — Step 3: Diagnosis**
> Open a case drill-down. "The diagnosis agent reads the failure context and explains why it
> happened — with a confidence score and recommended timing."

**0:40 — Step 4–5: Recoverable + strategy breakdown**
> Switch to Strategy Performance. "RAZOR scores every strategy by expected net recovery —
> retry, method switch, WhatsApp, email, discount — and picks the best one."

**1:00 — Step 6–7: Simulation + ₹ recovered vs baseline**
> Run the Simulation tab. "Run the simulation. RAZOR recovers ₹13.8L vs ₹7.4L baseline —
> that's the +₹7.22L incremental headline on the Overview."

**1:25 — Step 8: Drill-down timeline**
> Click a queue row → timeline modal. "Every decision is logged with reasoning and a full
> audit trail."

**1:40 — Step 9: Policy block**
> Show the guardrail rows in the timeline. "The policy engine is a hard gate — a discount
> above the merchant's limit is blocked automatically and sent for review."

**1:55 — Step 10: Learning loop**
> "After each case, recovery memory updates the customer profile, and experiment results
> tune strategy weights — RAZOR self-optimizes."

**2:05 — Close**
> "AI decides, ML predicts, rules protect, APIs execute, and data proves. That's RAZOR."

## Tips
- Record at 1080p, window maximized, browser zoom ~100%.
- Speak over the screen; use the tabs as beats.
- If Gemini key is absent, mention the rule-based fallback still produces diagnosis.
