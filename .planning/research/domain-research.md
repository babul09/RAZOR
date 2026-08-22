# RAZOR — Domain Research

## Payment Failure Landscape (India)

### Failure Rate Context
- UPI failure rates in India: ~2-5% of transactions (NPCI data)
- Card decline rates: ~8-15% depending on segment and bank
- Failed payment recovery without intervention: ~12-18% (internal Razorpay-style estimates)
- Industry best practice systems claim 25-35% recovery rates with intelligent intervention

### Failure Code Taxonomy
| Code | Category | Recovery Difficulty | Best Strategy |
|------|----------|---------------------|---------------|
| INSUFFICIENT_FUNDS | Liquidity | Low (temporary) | WAIT + RETRY |
| CARD_DECLINED | Bank block | Medium | PAYMENT_METHOD_SWITCH |
| UPI_FAILURE | Technical | Low | RETRY immediately or SWITCH |
| AUTHENTICATION_FAILED | Auth | Medium | PAYMENT_LINK (fresh flow) |
| NETWORK_ERROR | Technical | Very Low | RETRY (immediate) |
| FRAUD_SUSPECTED | Risk | High | HUMAN_ESCALATION |

### Revenue at Risk — Indian Context
- Average ticket size: ₹1,200 (small) to ₹85,000 (subscription/B2B)
- High-value recovery worth human escalation: ₹5,000+
- UPI transaction max: ₹1L (per transaction limit)

## Competitive Landscape

### Existing Solutions
| Product | Approach | Gap |
|---------|----------|-----|
| Chargebee Receivables | Rule-based dunning | No ML, no LLM diagnosis |
| Stripe Adaptive Acceptance | ML at gateway level | No post-failure recovery agent |
| Razorpay Smart Collect | Basic retry logic | No strategy engine |
| Recurly Revenue Recovery | Email campaigns | No real-time autonomous agent |

### RAZOR's Differentiation
1. **Closed-loop** — ingest → recover → verify → learn, not just "send reminder"
2. **Strategy engine** — picks best action by expected net recovery, not rule order
3. **WAIT as a strategy** — knows when NOT to act (industry first)
4. **Policy guardrails** — merchant-controlled safety layer (production-ready mental model)
5. **Self-optimizing** — experiment engine updates strategy weights from outcomes

## ML Benchmark References

### Recovery Prediction Models in Literature
- Logistic regression on payment data: ~68-72% AUC
- Gradient boosted trees: ~78-84% AUC
- Neural networks: marginal improvement, much higher complexity
- **Target for hackathon**: XGBoost at ~80% AUC on synthetic data

### Feature Importance (Expected)
1. `failure_code` — highest signal
2. `customer_ltv` — segments that are worth recovering
3. `previous_recovery_success_rate` — strongest behavioral signal
4. `historical_payment_hour` — timing matters
5. `transaction_amount` — higher value = more effort justified

## LLM Use Case Research

### Gemini for Payment Diagnosis
- Gemini Pro: best for multi-step reasoning with structured output
- Gemini Flash: best for explanation generation (cost-efficient)
- Structured output (JSON mode): available in Gemini API
- Recommended pattern: system prompt with schema + few-shot examples

### Prompt Engineering Notes
- Few-shot examples dramatically improve consistency of diagnosis
- Chain-of-thought improves `confidence` calibration
- Keep diagnosis calls async — p95 latency ~1-3s, not acceptable for synchronous flow

## Tech Stack Research

### FastAPI + Celery Pattern
- FastAPI handles HTTP requests, returns immediately
- Celery workers handle: LLM calls, ML inference, action execution
- Redis as both Celery broker and dashboard metric cache
- Pattern: `/cases/{id}` returns case + polls for diagnosis status

### PostgreSQL Schema Best Practices
- Use `BIGINT` for paise amounts (never FLOAT for money)
- JSONB for `diagnosis_output`, `strategy_evaluation`, `policy_check_result`
- Partial indexes on `recovery_cases(status)` for queue queries
- `audit_logs` table: append-only, no updates

### Next.js Dashboard Architecture
- Server components for initial data load (SSR for SEO/LCP)
- Client components for real-time queue updates
- Polling interval: 5s for live queue (acceptable for hackathon)
- Recharts for all charts (lighter than D3, good enough for demo)
