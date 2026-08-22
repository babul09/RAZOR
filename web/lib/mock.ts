/** Mock fallback data (used when the backend is unreachable). */

import type { CaseDetail, CaseSummary, Overview, StrategyMetric } from "./api";

export const mockOverview: Overview = {
  revenue_at_risk_paise: 48200000,
  recovered_paise: 13800000,
  recovery_rate: 0.286,
  total_cases: 20000,
  recovered_cases: 5720,
};

export const mockCases: CaseSummary[] = [
  {
    id: "case-1",
    customer_id: "cust-a",
    amount_at_risk_paise: 1200000,
    failure_code: "INSUFFICIENT_FUNDS",
    status: "STRATEGY_SELECTED",
    priority: 100,
    recovery_probability: 0.73,
    created_at: "2026-08-22 12:00:00",
  },
  {
    id: "case-2",
    customer_id: "cust-b",
    amount_at_risk_paise: 550000,
    failure_code: "UPI_FAILURE",
    status: "WAIT",
    priority: 80,
    recovery_probability: 0.62,
    created_at: "2026-08-22 12:01:00",
  },
  {
    id: "case-3",
    customer_id: "cust-c",
    amount_at_risk_paise: 900000,
    failure_code: "CARD_DECLINED",
    status: "AWAITING_APPROVAL",
    priority: 60,
    recovery_probability: 0.5,
    created_at: "2026-08-22 12:02:00",
  },
];

export const mockStrategies: StrategyMetric[] = [
  { strategy: "RETRY", attempts: 4200, recoveries: 3200, recovered_paise: 7100000, cost_paise: 840000 },
  { strategy: "WHATSAPP_REMINDER", attempts: 1800, recoveries: 1200, recovered_paise: 3100000, cost_paise: 180000 },
  { strategy: "PAYMENT_METHOD_SWITCH", attempts: 900, recoveries: 700, recovered_paise: 2300000, cost_paise: 270000 },
  { strategy: "EMAIL_REMINDER", attempts: 700, recoveries: 300, recovered_paise: 800000, cost_paise: 35000 },
];

export const mockCaseDetail: CaseDetail = {
  id: "case-1",
  customer_id: "cust-a",
  amount_at_risk_paise: 1200000,
  failure_code: "INSUFFICIENT_FUNDS",
  status: "STRATEGY_SELECTED",
  priority: 100,
  recovery_probability: 0.73,
  created_at: "2026-08-22 12:00:00",
  timeline: [
    { type: "audit", event_type: "DIAGNOSIS", detail: { diagnosis: "Insufficient balance" }, created_at: "2026-08-22 12:00:10" },
    { type: "decision", event_type: "AGENT_DECISION", detail: { selected_strategy: "WAIT", reasoning: "future EV better" }, created_at: "2026-08-22 12:00:20" },
    { type: "audit", event_type: "POLICY", detail: { status: "PASS" }, created_at: "2026-08-22 12:00:30" },
    { type: "audit", event_type: "BLOCK", detail: { reason: "discount exceeds max_discount_percent" }, created_at: "2026-08-22 12:00:40" },
  ],
};
