"use client";

import { useEffect, useState } from "react";

import { formatInr, getStrategies, type StrategyMetric } from "@/lib/api";

export default function StrategyPerformanceSection() {
  const [rows, setRows] = useState<StrategyMetric[]>([]);

  useEffect(() => {
    getStrategies().then(setRows);
  }, []);

  return (
    <section>
      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs text-slate-500">
            <tr>
              <th className="px-4 py-2">Strategy</th>
              <th className="px-4 py-2">Attempts</th>
              <th className="px-4 py-2">Recovery %</th>
              <th className="px-4 py-2">₹ recovered</th>
              <th className="px-4 py-2">Cost</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.strategy} className="border-b border-slate-100">
                <td className="px-4 py-2 font-medium">{r.strategy}</td>
                <td className="px-4 py-2">{r.attempts.toLocaleString()}</td>
                <td className="px-4 py-2">
                  {r.attempts ? `${((r.recoveries / r.attempts) * 100).toFixed(1)}%` : "—"}
                </td>
                <td className="px-4 py-2">{formatInr(r.recovered_paise)}</td>
                <td className="px-4 py-2">{formatInr(r.cost_paise)}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-slate-400">
                  No strategy data
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
