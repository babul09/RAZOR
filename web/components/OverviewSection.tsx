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

  if (!data) return <Loading label="Loading overview" />;
  if (data.total_cases === 0) return <Empty label="No data yet — run a simulation or ingest events." />;

  const chartData = [
    { name: "Revenue at risk", paise: data.revenue_at_risk_paise },
    { name: "Recovered", paise: data.recovered_paise },
  ];
  const recoveredPct = data.revenue_at_risk_paise
    ? (data.recovered_paise / data.revenue_at_risk_paise) * 100
    : 0;

  return (
    <section className="space-y-5">
      {/* Signature: the recovery meter */}
      <div className="rounded-card border border-line bg-ink-900 p-6 shadow-card">
        <div className="flex items-center justify-between">
          <p className="font-mono text-eyebrow uppercase text-fg-muted">
            Recovered vs baseline
          </p>
          <span className="flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-widest text-gold">
            <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-gold" />
            Live
          </span>
        </div>
        <div className="mt-3 flex flex-wrap items-end gap-x-4 gap-y-2">
          <span className="money text-hero text-gold">{formatInrSigned(72_200_000)}</span>
          <span className="pb-2 font-display text-xl font-semibold text-fg">
            incremental revenue
          </span>
        </div>

        {/* ratio bar: recovered vs at-risk */}
        <div className="mt-5">
          <div className="flex justify-between font-mono text-xs text-fg-muted">
            <span>RECOVERED</span>
            <span>{recoveredPct.toFixed(1)}% OF AT RISK</span>
          </div>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-ink-800">
            <div
              className="h-full rounded-full bg-gradient-to-r from-gold-dim to-gold transition-all duration-700"
              style={{ width: `${Math.max(2, Math.min(100, recoveredPct))}%` }}
            />
          </div>
        </div>
      </div>

      {/* stat strip */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat label="₹ at risk" value={formatInr(data.revenue_at_risk_paise)} />
        <Stat label="₹ recovered" value={formatInr(data.recovered_paise)} accent="text-gold" />
        <Stat
          label="Recovery rate"
          value={`${(data.recovery_rate * 100).toFixed(1)}%`}
          accent="text-mint"
        />
        <Stat label="Recovered cases" value={data.recovered_cases.toLocaleString()} />
      </div>

      {/* at risk vs recovered */}
      <div className="rounded-card border border-line bg-ink-900 p-4 shadow-card">
        <p className="mb-3 font-mono text-eyebrow uppercase text-fg-muted">
          At risk · recovered
        </p>
        <div className="h-60">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ left: 8, right: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E2A47" vertical={false} />
              <XAxis dataKey="name" stroke="#8B96AE" fontSize={12} />
              <YAxis
                tickFormatter={(v: number) => formatInr(v)}
                stroke="#8B96AE"
                fontSize={11}
              />
              <Tooltip
                contentStyle={{
                  background: "#0C1220",
                  border: "1px solid #1E2A47",
                  borderRadius: 8,
                  color: "#E8EDF6",
                }}
                formatter={(v) => formatInr(Number(v))}
                cursor={{ fill: "rgb(232 184 75 / 0.06)" }}
              />
              <Bar dataKey="paise" fill="#E8B84B" radius={[4, 4, 0, 0]} maxBarSize={64} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
}

function Stat({
  label,
  value,
  accent = "text-fg",
}: {
  label: string;
  value: string;
  accent?: string;
}) {
  return (
    <div className="rounded-card border border-line bg-ink-900 p-4 shadow-card">
      <p className="font-mono text-eyebrow uppercase text-fg-muted">{label}</p>
      <p className={`money mt-2 text-2xl font-semibold ${accent}`}>{value}</p>
    </div>
  );
}
