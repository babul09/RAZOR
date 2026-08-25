"use client";

import { useState } from "react";

import {
  formatInr,
  formatInrSigned,
  getSimulationStatus,
  runSimulation,
  type SimulationStatus,
} from "@/lib/api";

interface SimBaseline {
  total_recovered_paise: number;
  recovery_rate: number;
  total_interventions: number;
  total_discount_cost_paise: number;
  net_recovered_paise: number;
}

interface StrategySlice {
  attempts: number;
  recoveries: number;
  revenue_recovered_paise: number;
  cost_paise: number;
}

interface SimRazor extends SimBaseline {
  total_events: number;
  total_revenue_at_risk_paise: number;
  strategy_breakdown: Record<string, StrategySlice>;
}

interface SimulationResult {
  incremental_paise: number;
  baseline: SimBaseline;
  razor: SimRazor;
}

const STAGES = [
  { key: "generating", label: "Generating synthetic events" },
  { key: "baseline", label: "Running baseline recovery" },
  { key: "razor", label: "Running RAZOR policy pipeline" },
  { key: "complete", label: "Complete" },
];

function ProgressBar({
  label,
  pct,
  active,
  done,
}: {
  label: string;
  pct: number;
  active: boolean;
  done: boolean;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between font-mono text-xs text-fg-muted">
        <span className={active ? "text-gold" : done ? "text-mint" : "text-fg-muted"}>
          {active ? "▸ " : done ? "✓ " : "○ "}
          {label}
        </span>
        <span className="text-fg-muted/70">{Math.round(pct)}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-ink-800">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            done ? "bg-mint" : active ? "bg-gold" : "bg-ink-700"
          }`}
          style={{ width: `${Math.max(2, pct)}%` }}
        />
      </div>
    </div>
  );
}

function Bar({ label, paise, max, accent }: {
  label: string;
  paise: number;
  max: number;
  accent: string;
}) {
  const pct = max > 0 ? (paise / max) * 100 : 0;
  return (
    <div className="space-y-1">
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-[11px] uppercase tracking-wider text-fg-muted">{label}</span>
        <span className={`money font-mono text-sm ${accent}`}>{formatInr(paise)}</span>
      </div>
      <div className="h-2.5 overflow-hidden rounded-full bg-ink-800">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${Math.max(pct, 1)}%`, background: pct > 0 ? undefined : "transparent" }}
        />
      </div>
    </div>
  );
}

export default function SimulationSection() {
  const [n, setN] = useState(10000);
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState<SimulationStatus | null>(null);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleRun() {
    setRunning(true);
    setError(null);
    setResult(null);
    setStatus(null);
    try {
      const { job_id } = await runSimulation(n);
      // Poll until a terminal state, tracking live stage progress.
      for (;;) {
        const s = await getSimulationStatus(job_id);
        setStatus(s);
        if (s.status === "succeeded") {
          setResult(s.result as unknown as SimulationResult);
          break;
        }
        if (s.status === "failed") {
          setError(s.error || "Simulation failed");
          break;
        }
        await new Promise((r) => setTimeout(r, 500));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Simulation failed");
    } finally {
      setRunning(false);
    }
  }

  const stageIndex = status ? STAGES.findIndex((s) => s.key === status.stage) : -1;
  const pct =
    status && status.total
      ? ((status.completed ?? 0) / status.total) * 100
      : running
        ? 5
        : 0;

  const rows = result
    ? [
        { metric: "Revenue recovered", b: result.baseline.total_recovered_paise, r: result.razor.total_recovered_paise },
        { metric: "Recovery rate", b: result.baseline.recovery_rate, r: result.razor.recovery_rate, pct: true },
        { metric: "Net recovered", b: result.baseline.net_recovered_paise, r: result.razor.net_recovered_paise },
        { metric: "Discount cost", b: result.baseline.total_discount_cost_paise, r: result.razor.total_discount_cost_paise },
        { metric: "Interventions", b: result.baseline.total_interventions, r: result.razor.total_interventions },
      ]
    : [];

  const maxRecovered = result
    ? Math.max(result.baseline.total_recovered_paise, result.razor.total_recovered_paise)
    : 1;

  const breakdown = result ? Object.entries(result.razor.strategy_breakdown ?? {}) : [];

  return (
    <section className="space-y-4">
      <div className="flex items-baseline justify-between">
        <p className="font-mono text-eyebrow uppercase text-fg-muted">Simulation</p>
        <p className="font-mono text-[11px] text-fg-muted/70">baseline · naive retry vs RAZOR policy</p>
      </div>

      <div className="flex flex-wrap items-end gap-3 rounded-card border border-line bg-ink-900 p-4 shadow-card">
        <label className="font-mono text-xs text-fg-muted">
          Events
          <input
            type="number"
            value={n}
            min={100}
            step={100}
            onChange={(e) => setN(Number(e.target.value))}
            className="ml-2 rounded border border-line bg-ink-800 px-2 py-1 font-mono text-fg focus:border-gold"
          />
        </label>
        <button
          onClick={handleRun}
          disabled={running}
          className="rounded-card bg-gold px-4 py-2 font-display text-sm font-semibold text-ink-950 transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {running ? "Running…" : "Run recovery simulation"}
        </button>
      </div>

      {error && <p className="font-mono text-sm text-rose">{error}</p>}

      {/* Live stage progress while the simulation runs. */}
      {running && (
        <div className="rounded-card border border-gold/30 bg-ink-900 p-5 shadow-card">
          <div className="mb-4 flex items-center justify-between">
            <p className="font-mono text-eyebrow uppercase text-fg-muted">
              Running simulation
            </p>
            <span className="animate-pulse-soft font-mono text-xs uppercase tracking-widest text-gold">
              live
            </span>
          </div>
          <div className="space-y-4">
            {STAGES.map((s, i) => (
              <ProgressBar
                key={s.key}
                label={s.label}
                pct={i < stageIndex ? 100 : i === stageIndex ? pct : 0}
                active={i === stageIndex}
                done={i < stageIndex || (status?.status === "succeeded" && i <= stageIndex)}
              />
            ))}
          </div>
          {status?.stage && stageIndex >= 0 && (
            <p className="mt-4 font-mono text-sm text-fg">
              {STAGES[stageIndex].label}…
            </p>
          )}
        </div>
      )}

      {result && (
        <>
          {/* Hero: the incremental number is the thesis. */}
          <div className="rounded-card border border-gold/30 bg-ink-900 p-5 shadow-card">
            <p className="font-mono text-[11px] uppercase tracking-wider text-fg-muted">
              Incremental recovery vs baseline
            </p>
            <p className="money font-display text-hero text-mint">
              {formatInrSigned(result.incremental_paise)}
            </p>
            <div className="mt-3 flex flex-wrap gap-4 font-mono text-xs text-fg-muted">
              <span>
                RAZOR rate{" "}
                <span className="text-fg">{(result.razor.recovery_rate * 100).toFixed(1)}%</span>
              </span>
              <span>
                Baseline rate{" "}
                <span className="text-fg">{(result.baseline.recovery_rate * 100).toFixed(1)}%</span>
              </span>
              <span>
                {result.razor.total_events.toLocaleString()} events
              </span>
            </div>
          </div>

          {/* Dual bars: where the money lands. */}
          <div className="grid gap-4 rounded-card border border-line bg-ink-900 p-4 shadow-card sm:grid-cols-2">
            <Bar label="Baseline recovered" paise={result.baseline.total_recovered_paise} max={maxRecovered} accent="text-fg-muted" />
            <Bar label="RAZOR recovered" paise={result.razor.total_recovered_paise} max={maxRecovered} accent="text-gold" />
          </div>

          {/* Comparison table. */}
          <div className="overflow-x-auto rounded-card border border-line bg-ink-900 shadow-card">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-line bg-ink-800/60 font-mono text-[11px] uppercase tracking-wider text-fg-muted">
                <tr>
                  <th className="px-4 py-3 font-medium">Metric</th>
                  <th className="px-4 py-3 text-right font-medium">Baseline</th>
                  <th className="px-4 py-3 text-right font-medium">RAZOR</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.metric} className="border-b border-line/60">
                    <td className="px-4 py-2.5 font-display text-fg">{r.metric}</td>
                    <td className="money px-4 py-2.5 text-right text-fg-muted">
                      {r.pct ? `${(r.b * 100).toFixed(1)}%` : formatInr(r.b)}
                    </td>
                    <td className="money px-4 py-2.5 text-right text-gold">
                      {r.pct ? `${(r.r * 100).toFixed(1)}%` : formatInr(r.r)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Strategy attribution: where the incremental money comes from. */}
          <div className="overflow-x-auto rounded-card border border-line bg-ink-900 shadow-card">
            <div className="border-b border-line bg-ink-800/60 px-4 py-2.5 font-mono text-[11px] uppercase tracking-wider text-fg-muted">
              Strategy attribution
            </div>
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-line bg-ink-800/40 font-mono text-[11px] uppercase tracking-wider text-fg-muted">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Strategy</th>
                  <th className="px-4 py-2.5 text-right font-medium">Attempts</th>
                  <th className="px-4 py-2.5 text-right font-medium">Recovery %</th>
                  <th className="px-4 py-2.5 text-right font-medium">₹ recovered</th>
                  <th className="px-4 py-2.5 text-right font-medium">Cost</th>
                </tr>
              </thead>
              <tbody>
                {breakdown.map(([name, s]) => (
                  <tr key={name} className="border-b border-line/60">
                    <td className="px-4 py-2.5 font-display text-fg">{name.replace(/_/g, " ")}</td>
                    <td className="money px-4 py-2.5 text-right text-fg">{s.attempts.toLocaleString()}</td>
                    <td className="money px-4 py-2.5 text-right text-mint">
                      {s.attempts ? `${((s.recoveries / s.attempts) * 100).toFixed(1)}%` : "—"}
                    </td>
                    <td className="money px-4 py-2.5 text-right text-gold">{formatInr(s.revenue_recovered_paise)}</td>
                    <td className="money px-4 py-2.5 text-right text-fg-muted">{formatInr(s.cost_paise)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {!result && !error && !running && (
        <p className="font-mono text-sm text-fg-muted">
          Run a simulation to project recovery across {n.toLocaleString()} events — baseline vs RAZOR.
        </p>
      )}
    </section>
  );
}
