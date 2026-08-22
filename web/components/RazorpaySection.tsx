"use client";

import { useCallback, useEffect, useState } from "react";

import {
  formatInr,
  formatInrSigned,
  getRazorpayComparison,
  getRazorpayHealth,
  getRazorpayPayments,
  razorpayRecover,
  type RazorpayComparison,
  type RazorpayHealth,
  type RazorpayPayment,
  type RazorpayRecover,
} from "@/lib/api";
import { Loading } from "./State";

function CmpBar({ label, paise, max, accent }: {
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

export default function RazorpaySection() {
  const [health, setHealth] = useState<RazorpayHealth | null>(null);
  const [cmp, setCmp] = useState<RazorpayComparison | null>(null);
  const [payments, setPayments] = useState<RazorpayPayment[]>([]);
  const [recovering, setRecovering] = useState<string | null>(null);
  const [recovered, setRecovered] = useState<RazorpayRecover | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    getRazorpayHealth().then(setHealth);
    getRazorpayComparison(50).then(setCmp);
    getRazorpayPayments(50).then(setPayments);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleRecover(p: RazorpayPayment) {
    setRecovering(p.id);
    setError(null);
    setRecovered(null);
    try {
      const r = await razorpayRecover(p.id, {
        name: p.email?.split("@")[0] || undefined,
        email: p.email || undefined,
        contact: p.contact || undefined,
      });
      setRecovered(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Recovery failed");
    } finally {
      setRecovering(null);
    }
  }

  if (!health || !cmp) return <Loading label="Loading Razorpay live feed" />;

  const demo = !health.configured;
  const sample = cmp.source === "sample";
  const maxRecovered = Math.max(cmp.baseline.total_recovered_paise, cmp.razor.total_recovered_paise, 1);

  return (
    <section className="space-y-4">
      {/* Razorpay-branded header — a slice of the payment-link checkout. */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-card border border-line bg-rpay-navy px-4 py-3 shadow-card">
        <div className="flex items-center gap-3">
          <span className="grid h-9 w-9 place-items-center rounded-[0.5rem] bg-rpay-blue font-display text-lg font-black text-white">
            R
          </span>
          <div className="leading-tight">
            <p className="font-display text-sm font-bold tracking-wide text-white">Razorpay</p>
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/60">
              recovery terminal · live
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-wider text-white/80">
            <span className={`h-2 w-2 rounded-full ${demo ? "bg-white/40" : "bg-mint"}`} />
            {demo ? "demo mode" : "test api connected"}
          </span>
          {health.key_id_masked && (
            <span className="hidden rounded-full border border-white/20 px-2 py-0.5 font-mono text-[10px] text-white/70 sm:inline">
              {health.key_id_masked}
            </span>
          )}
        </div>
      </div>

      {sample && (
        <p className="rounded-card border border-rpay-blue/30 bg-ink-900 p-3 font-mono text-xs text-fg-muted">
          {demo ? (
            <>No test keys set — showing sample data. Add <span className="text-rpay-light">RAZORPAY_KEY_ID</span> / <span className="text-rpay-light">RAZORPAY_KEY_SECRET</span> to <span className="text-fg">.env</span>.</>
          ) : (
            <>Live keys connected, but the test account has no failed payments yet — showing sample data. "Recover" still creates a <span className="text-rpay-light">real payment link</span> on the test API.</>
          )}
        </p>
      )}

      {/* Side-by-side comparison — the thesis. */}
      {cmp.at_risk_paise > 0 && (
        <>
          <div className="rounded-card border border-rpay-blue/30 bg-ink-900 p-5 shadow-card">
            <p className="font-mono text-[11px] uppercase tracking-wider text-fg-muted">
              Incremental recovery vs baseline · {formatInr(cmp.at_risk_paise)} at risk
            </p>
            <p className="money font-display text-hero text-rpay-light">
              {formatInrSigned(cmp.incremental_paise)}
            </p>
            <div className="mt-3 flex flex-wrap gap-4 font-mono text-xs text-fg-muted">
              <span>RAZOR rate <span className="text-rpay-light">{(cmp.razor.recovery_rate * 100).toFixed(1)}%</span></span>
              <span>Baseline rate <span className="text-fg">{(cmp.baseline.recovery_rate * 100).toFixed(1)}%</span></span>
              <span>{payments.length} failed payments</span>
            </div>
          </div>

          <div className="grid gap-4 rounded-card border border-line bg-ink-900 p-4 shadow-card sm:grid-cols-2">
            <CmpBar label="Baseline recovered" paise={cmp.baseline.total_recovered_paise} max={maxRecovered} accent="text-fg-muted" />
            <CmpBar label="RAZOR recovered" paise={cmp.razor.total_recovered_paise} max={maxRecovered} accent="text-rpay-light" />
          </div>

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
                {[
                  { m: "Revenue recovered", b: cmp.baseline.total_recovered_paise, r: cmp.razor.total_recovered_paise },
                  { m: "Recovery rate", b: cmp.baseline.recovery_rate, r: cmp.razor.recovery_rate, pct: true },
                  { m: "Net recovered", b: cmp.baseline.net_recovered_paise, r: cmp.razor.net_recovered_paise },
                  { m: "Interventions", b: cmp.baseline.interventions, r: cmp.razor.interventions, count: true },
                ].map((row) => (
                  <tr key={row.m} className="border-b border-line/60">
                    <td className="px-4 py-2.5 font-display text-fg">{row.m}</td>
                    <td className="money px-4 py-2.5 text-right text-fg-muted">
                      {row.pct ? `${(row.b * 100).toFixed(1)}%` : row.count ? row.b : formatInr(row.b)}
                    </td>
                    <td className="money px-4 py-2.5 text-right text-rpay-light">
                      {row.pct ? `${(row.r * 100).toFixed(1)}%` : row.count ? row.r : formatInr(row.r)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* Recovery result */}
      {recovered && recovered.short_url && (
        <div className="rounded-card border border-rpay-blue/40 bg-ink-900 p-4 shadow-card">
          <p className="font-mono text-[11px] uppercase tracking-wider text-rpay-light">Payment link created</p>
          <div className="mt-1 flex flex-wrap items-center gap-3">
            <a
              href={recovered.short_url}
              target="_blank"
              rel="noreferrer"
              className="font-mono text-sm text-rpay-light underline underline-offset-4"
            >
              {recovered.short_url}
            </a>
            <span className="font-mono text-xs text-fg-muted">
              {recovered.strategy.replace(/_/g, " ")} · {(recovered.recovery_probability * 100).toFixed(1)}% · {formatInr(recovered.amount_paise)}
            </span>
          </div>
        </div>
      )}
      {error && <p className="font-mono text-sm text-rose">{error}</p>}

      {/* Live failed payments */}
      <div className="overflow-x-auto rounded-card border border-line bg-ink-900 shadow-card">
        <div className="flex items-center justify-between border-b border-line bg-ink-800/60 px-4 py-2.5">
          <span className="font-mono text-[11px] uppercase tracking-wider text-fg-muted">Failed payments</span>
          <button
            onClick={load}
            className="font-mono text-[11px] uppercase tracking-wider text-rpay-light hover:underline"
          >
            refresh
          </button>
        </div>
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-line bg-ink-800/40 font-mono text-[11px] uppercase tracking-wider text-fg-muted">
            <tr>
              <th className="px-4 py-2.5 font-medium">Payment</th>
              <th className="px-4 py-2.5 text-right font-medium">Amount</th>
              <th className="px-4 py-2.5 font-medium">Issue</th>
              <th className="px-4 py-2.5 font-medium">Method</th>
              <th className="px-4 py-2.5 text-right font-medium">Action</th>
            </tr>
          </thead>
          <tbody>
            {payments.slice(0, 12).map((p) => (
              <tr key={p.id} className="border-b border-line/60">
                <td className="px-4 py-2.5 font-mono text-xs text-fg">{p.id}</td>
                <td className="money px-4 py-2.5 text-right text-fg">{formatInr(p.amount_paise)}</td>
                <td className="px-4 py-2.5 text-fg-muted">{p.failure_code?.replace(/_/g, " ") || "—"}</td>
                <td className="px-4 py-2.5 text-fg-muted">{p.method}</td>
                <td className="px-4 py-2.5 text-right">
                  <button
                    onClick={() => handleRecover(p)}
                    disabled={recovering === p.id}
                    className="rounded-card bg-rpay-blue px-3 py-1 font-mono text-xs font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                  >
                    {recovering === p.id ? "…" : "Recover"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
