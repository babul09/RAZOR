/** Typed API client for the RAZOR FastAPI backend, with mock fallback. */

import {
  mockOverview,
  mockCases,
  mockStrategies,
  mockCaseDetail,
} from "./mock";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface CaseSummary {
  id: string;
  customer_id: string;
  amount_at_risk_paise: number;
  failure_code: string | null;
  status: string;
  priority: number;
  recovery_probability: number | null;
  created_at: string | null;
}

export interface TimelineEntry {
  type: string;
  event_type: string;
  detail: Record<string, unknown> | null;
  created_at: string | null;
}

export interface CaseDetail extends CaseSummary {
  timeline: TimelineEntry[];
}

export interface Overview {
  revenue_at_risk_paise: number;
  recovered_paise: number;
  recovery_rate: number;
  total_cases: number;
  recovered_cases: number;
}

export interface StrategyMetric {
  strategy: string;
  attempts: number;
  recoveries: number;
  recovered_paise: number;
  cost_paise: number;
}

export interface SimulationStatus {
  status: string;
  result: Record<string, unknown> | null;
}

export interface RazorpayHealth {
  configured: boolean;
  mode: string;
  key_id_masked: string | null;
}

export interface RazorpayPayment {
  id: string;
  amount_paise: number;
  currency: string;
  status: string;
  method: string;
  email: string | null;
  contact: string | null;
  failure_code: string | null;
  failure_reason: string | null;
  created_at: number | null;
}

export interface RazorpayLink {
  id: string;
  amount_paise: number;
  status: string;
  short_url: string | null;
  created_at: number | null;
}

export interface RazorpaySimSide {
  total_recovered_paise: number;
  recovery_rate: number;
  net_recovered_paise: number;
  interventions: number;
}

export interface RazorpayComparison {
  configured: boolean;
  at_risk_paise: number;
  baseline: RazorpaySimSide;
  razor: RazorpaySimSide;
  incremental_paise: number;
}

export interface RazorpayRecover {
  payment_id: string;
  amount_paise: number;
  strategy: string;
  recovery_probability: number;
  link_id: string | null;
  short_url: string | null;
  link_status: string | null;
}

async function getJson<T>(path: string, fallback: T): Promise<T> {
  try {
    const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
    if (!res.ok) return fallback;
    return (await res.json()) as T;
  } catch {
    return fallback;
  }
}

export function getOverview(): Promise<Overview> {
  return getJson("/api/analytics/overview", mockOverview);
}

export function getCases(): Promise<CaseSummary[]> {
  return getJson<{ items: CaseSummary[] }>("/api/recovery/cases?page=1&page_size=50", {
    items: mockCases,
  }).then((r) => r.items);
}

export function getStrategies(): Promise<StrategyMetric[]> {
  return getJson("/api/analytics/strategies", mockStrategies);
}

export function getCaseDetail(id: string): Promise<CaseDetail> {
  const fallback = { ...mockCaseDetail, id };
  return getJson(`/api/recovery/cases/${id}`, fallback);
}

export async function runSimulation(
  n: number
): Promise<{ job_id: string }> {
  try {
    const res = await fetch(`${API_URL}/api/simulation/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ n_events: n, seed: 42, hour: 14 }),
    });
    if (!res.ok) throw new Error("simulation run failed");
    return await res.json();
  } catch {
    return { job_id: "mock" };
  }
}

export function getSimulationStatus(jobId: string): Promise<SimulationStatus> {
  const fallback: SimulationStatus = {
    status: "SUCCESS",
    result: {
      incremental_paise: 722000,
      baseline: { total_recovered_paise: 740000 },
      razor: { total_recovered_paise: 1380000 },
    },
  };
  return getJson(`/api/simulation/status/${jobId}`, fallback);
}

export function getRazorpayHealth(): Promise<RazorpayHealth> {
  return getJson("/api/razorpay/health", {
    configured: false,
    mode: "demo",
    key_id_masked: null,
  });
}

export function getRazorpayPayments(count = 50): Promise<RazorpayPayment[]> {
  return getJson(`/api/razorpay/payments?count=${count}`, []);
}

export function getRazorpayLinks(count = 25): Promise<RazorpayLink[]> {
  return getJson(`/api/razorpay/links?count=${count}`, []);
}

export function getRazorpayComparison(count = 50): Promise<RazorpayComparison> {
  const empty: RazorpayComparison = {
    configured: false,
    at_risk_paise: 0,
    baseline: { total_recovered_paise: 0, recovery_rate: 0, net_recovered_paise: 0, interventions: 0 },
    razor: { total_recovered_paise: 0, recovery_rate: 0, net_recovered_paise: 0, interventions: 0 },
    incremental_paise: 0,
  };
  return getJson(`/api/razorpay/comparison?count=${count}`, empty);
}

export async function razorpayRecover(
  paymentId: string,
  customer?: { name?: string; email?: string; contact?: string }
): Promise<RazorpayRecover> {
  try {
    const res = await fetch(`${API_URL}/api/razorpay/recover`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ payment_id: paymentId, ...customer }),
    });
    if (!res.ok) throw new Error("recover failed");
    return await res.json();
  } catch {
    return {
      payment_id: paymentId,
      amount_paise: 0,
      strategy: "RETRY",
      recovery_probability: 0.5,
      link_id: null,
      short_url: null,
      link_status: null,
    };
  }
}

export function formatInr(paise: number): string {
  const rupees = paise / 100;
  if (rupees >= 100000) return `₹${(rupees / 100000).toFixed(2)}L`;
  return `₹${Math.round(rupees).toLocaleString("en-IN")}`;
}

/** Format a signed paise value as +/− ₹ for headline/delta display. */
export function formatInrSigned(paise: number): string {
  const rupees = paise / 100;
  const sign = rupees >= 0 ? "+" : "−";
  let body: string;
  if (Math.abs(rupees) >= 100000) {
    body = `₹${(Math.abs(rupees) / 100000).toFixed(2)}L`;
  } else {
    body = `₹${Math.round(Math.abs(rupees)).toLocaleString("en-IN")}`;
  }
  return `${sign}${body}`;
}
