"use client";

import { useEffect, useState } from "react";

import { API_URL, formatInr, getCases, type CaseSummary } from "@/lib/api";
import { Empty, Loading } from "./State";

const statusStyles: Record<string, string> = {
  NEW: "bg-ink-700 text-fg-muted",
  STRATEGY_SELECTED: "bg-gold/15 text-gold",
  WAIT: "bg-amber-500/15 text-amber-700",
  STOPPED: "bg-ink-700 text-fg-muted",
  AWAITING_APPROVAL: "bg-orange-500/15 text-orange-700",
  RECOVERED: "bg-mint/15 text-mint",
  FAILED: "bg-rose/15 text-rose",
};

export default function RecoveryQueueSection({
  onSelect,
}: {
  onSelect: (caseId: string) => void;
}) {
  const [cases, setCases] = useState<CaseSummary[] | null>(null);

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
    <section className="space-y-3">
      <p className="font-mono text-eyebrow uppercase text-fg-muted">
        Live recovery queue · SSE
      </p>
      <div className="overflow-x-auto rounded-card border border-line bg-ink-900 shadow-card">
        {cases === null ? (
          <Loading label="Loading recovery queue" />
        ) : (
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-line bg-ink-800/60 font-mono text-[11px] uppercase tracking-wider text-fg-muted">
              <tr>
                <th className="px-4 py-3 font-medium">Customer</th>
                <th className="px-4 py-3 text-right font-medium">Amount</th>
                <th className="px-4 py-3 font-medium">Issue</th>
                <th className="px-4 py-3 text-right font-medium">P(rec)</th>
                <th className="px-4 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => (
                <tr
                  key={c.id}
                  className="cursor-pointer border-b border-line/60 transition-colors hover:bg-ink-800/40"
                  onClick={() => onSelect(c.id)}
                >
                  <td className="px-4 py-2.5 font-mono text-fg">
                    {c.customer_id.slice(0, 8)}
                  </td>
                  <td className="money px-4 py-2.5 text-right text-gold">
                    {formatInr(c.amount_at_risk_paise)}
                  </td>
                  <td className="px-4 py-2.5 text-fg-muted">{c.failure_code || "—"}</td>
                  <td className="money px-4 py-2.5 text-right text-fg">
                    {c.recovery_probability != null
                      ? `${(c.recovery_probability * 100).toFixed(0)}%`
                      : "—"}
                  </td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`rounded-full px-2 py-0.5 font-mono text-[11px] ${
                        statusStyles[c.status] || "bg-ink-700 text-fg-muted"
                      }`}
                    >
                      {c.status}
                    </span>
                  </td>
                </tr>
              ))}
              {cases.length === 0 && (
                <tr>
                  <td colSpan={5}>
                    <Empty label="No recovery cases" />
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
