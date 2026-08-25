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

import {
  formatInr,
  formatInrSigned,
  getOverview,
  runRecoveryBatch,
  type Overview,
} from "@/lib/api";
import { Empty, Loading } from "./State";

export default function OverviewSection() {
  const [data, setData] = useState<Overview | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getOverview().then(setData);
  }, []);

  async function handleRunBatch() {
    setBusy(true);
    try {
      await runRecoveryBatch();
      setData(await getOverview());
    } finally {
      setBusy(false);
    }
  }

  if (!data) return <Loading label="Loading overview" />;
  if (data.total_cases === 0) return <Empty label="No data yet — run a simulation or ingest events." />;

  const recoveredPct = data.revenue_at_risk_paise
    ? Math.min(100, (data.recovered_paise / data.revenue_at_risk_paise) * 100)
    : 0;
  const hasMeasured =
    data.incremental_paise !== null && data.incremental_paise !== undefined;
  const maxSource = Math.max(
    ...data.by_source.map((s) => s.at_risk_paise),
    1,
  );

  return (
    <section className="space-y-5">
      {/* Signature: the dark recovery readout */}
      <div className="relative overflow-hidden rounded-card bg-console p-6 text-white shadow-card sm:p-8">
        <div className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-gold/10 blur-3xl" />
        <div className="flex items-center justify-between">
          <p className="font-mono text-eyebrow uppercase tracking-[0.22em] text-white/50">
            Measured · executed outcomes
          </p>
          <span className="flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-widest text-amber-300">
            <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-amber-300" />
            Live
          </span>
        </div>

        <div className="mt-4 flex flex-wrap items-end gap-x-5 gap-y-3">
          <div>
            {hasMeasured ? (
              <p className="money text-hero leading-none text-white">
                {formatInrSigned(data.incremental_paise!)}
              </p>
            ) : (
              <p className="money text-3xl font-semibold leading-none text-white/40">
                No executed batch yet
              </p>
            )}
            <p className="mt-2 font-display text-base text-white/70">
              incremental revenue vs baseline
            </p>
          </div>
          <button
            onClick={handleRunBatch}
            disabled={busy}
            className="mb-1 rounded-card bg-amber-400 px-4 py-2 font-mono text-xs font-bold uppercase tracking-widest text-console transition-transform hover:-translate-y-0.5 disabled:opacity-50"
          >
            {busy ? "Running batch…" : "Run recovery batch"}
          </button>
        </div>

        {/* recovered vs at-risk meter */}
        <div className="mt-6">
          <div className="flex justify-between font-mono text-[11px] text-white/50">
            <span>Recovered</span>
            <span>{recoveredPct.toFixed(1)}% of at-risk</span>
          </div>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-white/15">
            <div
              className="h-full rounded-full bg-gradient-to-r from-amber-500 to-emerald-400 transition-all duration-700"
              style={{ width: `${Math.max(2, recoveredPct)}%` }}
            />
          </div>
        </div>
      </div>

      {/* stat strip */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat label="₹ at risk" value={formatInr(data.revenue_at_risk_paise)} />
        <Stat label="₹ recovered" value={formatInr(data.recovered_paise)} accent="text-mint" />
        <Stat
          label="Recovery rate"
          value={`${(data.recovery_rate * 100).toFixed(1)}%`}
          accent="text-gold"
        />
        <Stat label="Recovered cases" value={data.recovered_cases.toLocaleString()} />
      </div>

      {/* per-source recovery */}
      <div className="rounded-card border border-line bg-ink-900 p-5 shadow-card">
        <div className="flex items-baseline justify-between">
          <p className="font-mono text-eyebrow uppercase text-fg-muted">
            Recovery by event type
          </p>
          <span className="font-mono text-[11px] text-fg-muted/70">
            measured · executed
          </span>
        </div>
        <div className="mt-4 space-y-3">
          {data.by_source.length === 0 && (
            <p className="font-mono text-sm text-fg-muted">
              Run a recovery batch to measure recovery per event type.
            </p>
          )}
          {data.by_source.map((s) => {
            const pct = s.at_risk_paise ? (s.recovered_paise / s.at_risk_paise) * 100 : 0;
            return (
              <div key={s.source_type} className="space-y-1">
                <div className="flex items-baseline justify-between">
                  <span className="font-mono text-[11px] uppercase tracking-wider text-fg-muted">
                    {s.source_type}
                  </span>
                  <span className="money font-mono text-sm text-fg">
                    {formatInr(s.recovered_paise)}{" "}
                    <span className="text-fg-muted">/ {formatInr(s.at_risk_paise)}</span>
                  </span>
                </div>
                <div className="flex h-2.5 gap-1 overflow-hidden rounded-full bg-ink-700">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-mint-dim to-mint transition-all duration-700"
                    style={{ width: `${Math.max(2, pct)}%` }}
                  />
                  <div
                    className="h-full bg-gold/20"
                    style={{ width: `${(s.at_risk_paise / maxSource) * 100 - Math.max(2, pct)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* at risk vs recovered */}
      <div className="rounded-card border border-line bg-ink-900 p-4 shadow-card">
        <p className="mb-3 font-mono text-eyebrow uppercase text-fg-muted">
          At risk · recovered
        </p>
        <div className="h-60">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData(data)} margin={{ left: 8, right: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E3E8EF" vertical={false} />
              <XAxis dataKey="name" stroke="#5B6B7A" fontSize={12} />
              <YAxis
                tickFormatter={(v: number) => formatInr(v)}
                stroke="#5B6B7A"
                fontSize={11}
              />
              <Tooltip
                contentStyle={{
                  background: "#FFFFFF",
                  border: "1px solid #E3E8EF",
                  borderRadius: 8,
                  color: "#101828",
                  boxShadow: "0 12px 28px -18px rgb(16 24 40 / 0.25)",
                }}
                formatter={(v) => formatInr(Number(v))}
                cursor={{ fill: "rgb(180 83 9 / 0.06)" }}
              />
              <Bar dataKey="paise" fill="#B45309" radius={[4, 4, 0, 0]} maxBarSize={64} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
}

function chartData(data: Overview) {
  return [
    { name: "Revenue at risk", paise: data.revenue_at_risk_paise },
    { name: "Recovered", paise: data.recovered_paise },
  ];
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
