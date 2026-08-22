"use client";

import { useEffect, useState } from "react";

import { API_URL, formatInr, getCases, type CaseSummary } from "@/lib/api";

const statusStyles: Record<string, string> = {
  NEW: "bg-slate-100 text-slate-700",
  STRATEGY_SELECTED: "bg-indigo-100 text-indigo-700",
  WAIT: "bg-amber-100 text-amber-700",
  STOPPED: "bg-slate-200 text-slate-500",
  AWAITING_APPROVAL: "bg-orange-100 text-orange-700",
  RECOVERED: "bg-emerald-100 text-emerald-700",
  FAILED: "bg-rose-100 text-rose-700",
};

export default function RecoveryQueueSection({
  onSelect,
}: {
  onSelect: (caseId: string) => void;
}) {
  const [cases, setCases] = useState<CaseSummary[]>([]);

  useEffect(() => {
    let active = true;
    getCases().then((c) => {
      if (active) setCases(c);
    });

    // Live updates via SSE (EventSource), fall back to polling on error.
    let source: EventSource | null = null;
    let pollTimer: ReturnType<typeof setInterval> | null = null;
    try {
      source = new EventSource(`${API_URL}/api/recovery/events`);
      source.onmessage = (event) => {
        try {
          const items = JSON.parse(event.data) as CaseSummary[];
          setCases(items);
        } catch {
          /* ignore malformed */
        }
      };
      source.onerror = () => {
        source?.close();
        pollTimer = setInterval(() => getCases().then(setCases), 5000);
      };
    } catch {
      pollTimer = setInterval(() => getCases().then(setCases), 5000);
    }

    return () => {
      active = false;
      source?.close();
      if (pollTimer) clearInterval(pollTimer);
    };
  }, []);

  return (
    <section>
      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs text-slate-500">
            <tr>
              <th className="px-4 py-2">Customer</th>
              <th className="px-4 py-2">Amount</th>
              <th className="px-4 py-2">Issue</th>
              <th className="px-4 py-2">Probability</th>
              <th className="px-4 py-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {cases.map((c) => (
              <tr
                key={c.id}
                className="cursor-pointer border-b border-slate-100 hover:bg-slate-50"
                onClick={() => onSelect(c.id)}
              >
                <td className="px-4 py-2 font-medium">{c.customer_id.slice(0, 8)}</td>
                <td className="px-4 py-2">{formatInr(c.amount_at_risk_paise)}</td>
                <td className="px-4 py-2">{c.failure_code || "—"}</td>
                <td className="px-4 py-2">
                  {c.recovery_probability != null
                    ? `${(c.recovery_probability * 100).toFixed(0)}%`
                    : "—"}
                </td>
                <td className="px-4 py-2">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      statusStyles[c.status] || "bg-slate-100 text-slate-700"
                    }`}
                  >
                    {c.status}
                  </span>
                </td>
              </tr>
            ))}
            {cases.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-slate-400">
                  No recovery cases
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
