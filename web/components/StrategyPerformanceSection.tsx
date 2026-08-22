"use client";

import { useEffect, useState } from "react";

import { formatInr, getStrategies, type StrategyMetric } from "@/lib/api";
import { Empty, Loading } from "./State";

export default function StrategyPerformanceSection() {
  const [rows, setRows] = useState<StrategyMetric[] | null>(null);

  useEffect(() => {
    getStrategies().then(setRows);
  }, []);

  if (!rows) return <Loading label="Loading strategies" />;
  if (rows.length === 0) return <Empty label="No strategy data yet." />;

  return (
    <section className="space-y-3">
      <p className="font-mono text-eyebrow uppercase text-fg-muted">
        Strategy performance
      </p>
      <div className="overflow-x-auto rounded-card border border-line bg-ink-900 shadow-card">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-line bg-ink-800/60 font-mono text-[11px] uppercase tracking-wider text-fg-muted">
            <tr>
              <th className="px-4 py-3 font-medium">Strategy</th>
              <th className="px-4 py-3 text-right font-medium">Attempts</th>
              <th className="px-4 py-3 text-right font-medium">Recovery %</th>
              <th className="px-4 py-3 text-right font-medium">₹ recovered</th>
              <th className="px-4 py-3 text-right font-medium">Cost</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.strategy} className="border-b border-line/60">
                <td className="px-4 py-2.5 font-display text-fg">{r.strategy}</td>
                <td className="money px-4 py-2.5 text-right text-fg">
                  {r.attempts.toLocaleString()}
                </td>
                <td className="money px-4 py-2.5 text-right text-mint">
                  {r.attempts ? `${((r.recoveries / r.attempts) * 100).toFixed(1)}%` : "—"}
                </td>
                <td className="money px-4 py-2.5 text-right text-gold">
                  {formatInr(r.recovered_paise)}
                </td>
                <td className="money px-4 py-2.5 text-right text-fg-muted">
                  {formatInr(r.cost_paise)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
