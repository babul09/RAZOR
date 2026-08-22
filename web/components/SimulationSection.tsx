"use client";

import { useState } from "react";

import {
  formatInr,
  getSimulationStatus,
  runSimulation,
  type SimulationStatus,
} from "@/lib/api";

export default function SimulationSection() {
  const [n, setN] = useState(10000);
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState<SimulationStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleRun() {
    setRunning(true);
    setError(null);
    setStatus(null);
    try {
      const { job_id } = await runSimulation(n);
      for (let i = 0; i < 40; i++) {
        await new Promise((r) => setTimeout(r, 1000));
        const s = await getSimulationStatus(job_id);
        setStatus(s);
        if (s.status === "SUCCESS" || s.status === "FAILURE") break;
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Simulation failed");
    } finally {
      setRunning(false);
    }
  }

  const result = status?.result as {
    incremental_paise?: number;
    baseline?: { total_recovered_paise?: number };
    razor?: { total_recovered_paise?: number };
  } | null;

  return (
    <section className="space-y-4">
      <p className="font-mono text-eyebrow uppercase text-fg-muted">
        Simulation
      </p>

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
      {status?.status === "PENDING" && (
        <p className="animate-pulse-soft font-mono text-sm text-fg-muted">
          Simulation in progress…
        </p>
      )}

      {result && (
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
              <tr className="border-b border-line/60">
                <td className="px-4 py-2.5 text-fg">Revenue recovered</td>
                <td className="money px-4 py-2.5 text-right text-fg-muted">
                  {formatInr(result.baseline?.total_recovered_paise ?? 0)}
                </td>
                <td className="money px-4 py-2.5 text-right text-gold">
                  {formatInr(result.razor?.total_recovered_paise ?? 0)}
                </td>
              </tr>
              <tr>
                <td className="px-4 py-2.5 font-display text-fg">Incremental revenue</td>
                <td className="px-4 py-2.5 text-right text-fg-muted">—</td>
                <td className="money px-4 py-2.5 text-right text-mint">
                  +{formatInr(result.incremental_paise ?? 0)}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
