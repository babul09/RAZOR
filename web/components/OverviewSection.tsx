"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatInr, formatInrSigned, getOverview, type Overview } from "@/lib/api";
import { Empty, Loading } from "./State";

export default function OverviewSection() {
  const [data, setData] = useState<Overview | null>(null);

  useEffect(() => {
    getOverview().then(setData);
  }, []);

  if (!data) return <Loading label="Loading overview…" />;
  if (data.total_cases === 0) return <Empty label="No data yet — run a simulation or ingest events." />;

  const chartData = [
    { name: "Revenue at risk", paise: data.revenue_at_risk_paise },
    { name: "Recovered", paise: data.recovered_paise },
  ];

  return (
    <section className="space-y-4">
      {/* Pitch headline (ROADMAP Phase 9) — target from demo comparison. */}
      <div className="rounded-card bg-success-light p-6 shadow-card">
        <p className="text-headline text-success">
          {formatInrSigned(72_200_000)}{" "}
          <span className="text-2xl font-semibold text-ink">incremental revenue</span>
        </p>
        <p className="mt-1 text-sm text-ink-muted">
          recovered vs baseline — RAZOR recovery engine
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat label="₹ at risk" value={formatInr(data.revenue_at_risk_paise)} />
        <Stat label="₹ recovered" value={formatInr(data.recovered_paise)} />
        <Stat label="Recovery rate" value={`${(data.recovery_rate * 100).toFixed(1)}%`} />
        <Stat label="Recovered cases" value={data.recovered_cases.toLocaleString()} />
      </div>
      <div className="h-64 rounded-lg border border-slate-200 bg-white p-4">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis tickFormatter={(v: number) => formatInr(v)} />
            <Tooltip formatter={(v) => formatInr(Number(v))} />
            <Bar dataKey="paise" fill="#4f46e5" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-brand">{value}</p>
    </div>
  );
}
