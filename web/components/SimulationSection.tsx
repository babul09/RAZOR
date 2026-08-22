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
      // Poll until SUCCESS/FAILURE.
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
      <div className="flex items-end gap-3 rounded-lg border border-slate-200 bg-white p-4">
        <label className="text-sm">
          Events
          <input
            type="number"
            value={n}
            min={100}
            step={100}
            onChange={(e) => setN(Number(e.target.value))}
            className="ml-2 rounded border border-slate-300 px-2 py-1"
          />
        </label>
        <button
          onClick={handleRun}
          disabled={running}
          className="rounded bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-dark disabled:opacity-50"
        >
          {running ? "Running…" : "Run Recovery Simulation"}
        </button>
      </div>

      {error && <p className="text-sm text-rose-600">{error}</p>}
      {status?.status === "PENDING" && <p className="text-sm text-slate-500">Simulation in progress…</p>}

      {result && (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs text-slate-500">
              <tr>
                <th className="px-4 py-2">Metric</th>
                <th className="px-4 py-2">Baseline</th>
                <th className="px-4 py-2">RAZOR</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-slate-100">
                <td className="px-4 py-2 font-medium">Revenue recovered</td>
                <td className="px-4 py-2">{formatInr(result.baseline?.total_recovered_paise ?? 0)}</td>
                <td className="px-4 py-2">{formatInr(result.razor?.total_recovered_paise ?? 0)}</td>
              </tr>
              <tr>
                <td className="px-4 py-2 font-medium">Incremental revenue</td>
                <td className="px-4 py-2">—</td>
                <td className="px-4 py-2 text-emerald-600">
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
