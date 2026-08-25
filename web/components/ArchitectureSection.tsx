"use client";

import { useEffect, useMemo, useState } from "react";

import { getCases, type CaseSummary } from "@/lib/api";
import { Empty, Loading } from "./State";

const STAGES: {
  key: string;
  title: string;
  tagline: string;
  blurb: string;
  statuses: string[];
  tone: "gold" | "mint" | "rose" | "dim";
}[] = [
  {
    key: "ingest",
    title: "Ingest",
    tagline: "Webhook · any revenue-risk event",
    blurb: "payment.failed, checkout.abandoned, subscription.failed, invoice.overdue",
    statuses: ["NEW", "DIAGNOSING"],
    tone: "dim",
  },
  {
    key: "diagnose",
    title: "Diagnose",
    tagline: "Gemini LLM reasons why",
    blurb: "structured diagnosis — never executes money",
    statuses: ["DIAGNOSING", "PREDICTED"],
    tone: "gold",
  },
  {
    key: "strategy",
    title: "Strategy",
    tagline: "ML scores every tactic",
    blurb: "P(recovery) × amount − cost, with WAIT / STOP",
    statuses: ["STRATEGY_SELECTED"],
    tone: "gold",
  },
  {
    key: "policy",
    title: "Policy gate",
    tagline: "hard guardrail before action",
    blurb: "discount caps, contact limits, human approval",
    statuses: ["POLICY_CHECK", "AWAITING_APPROVAL"],
    tone: "rose",
  },
  {
    key: "execute",
    title: "Execute & verify",
    tagline: "recovery action → measured outcome",
    blurb: "payment link, retry, reminder; outcome recorded in paise",
    statuses: ["EXECUTING", "VERIFYING"],
    tone: "mint",
  },
  {
    key: "close",
    title: "Close & learn",
    tagline: "recovered / failed → memory",
    blurb: "customer profile + strategy success rates update",
    statuses: ["RECOVERED", "FAILED", "STOPPED"],
    tone: "dim",
  },
];

const toneStyles: Record<string, string> = {
  dim: "border-line text-fg-muted",
  gold: "border-gold/30 text-gold",
  rose: "border-rose/30 text-rose",
  mint: "border-mint/30 text-mint",
};

export default function ArchitectureSection() {
  const [cases, setCases] = useState<CaseSummary[] | null>(null);

  useEffect(() => {
    let active = true;
    const load = () => getCases().then((c) => active && setCases(c));
    load();
    const timer = setInterval(load, 4000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  const counts = useMemo(() => {
    const map = new Map<string, number>();
    for (const stage of STAGES)
      for (const s of stage.statuses) map.set(s, 0);
    if (cases)
      for (const c of cases) if (map.has(c.status)) map.set(c.status, (map.get(c.status) ?? 0) + 1);
    return STAGES.map((stage) => ({
      stage,
      count: stage.statuses.reduce((acc, s) => acc + (map.get(s) ?? 0), 0),
    }));
  }, [cases]);

  if (cases === null) return <Loading label="Loading pipeline" />;

  const totalLive = counts.reduce((a, c) => a + c.count, 0);

  return (
    <section className="space-y-4">
      <div className="flex items-baseline justify-between">
        <p className="font-mono text-eyebrow uppercase text-fg-muted">
          Live architecture · how recovery flows
        </p>
        <p className="font-mono text-[11px] text-fg-muted/70">
          {totalLive} cases in pipeline · refreshes live
        </p>
      </div>

      {/* Pipeline rails */}
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {counts.map(({ stage, count }) => {
          const active = count > 0;
          return (
            <div
              key={stage.key}
              className={`rounded-card border bg-ink-900 p-4 shadow-card transition-all ${toneStyles[stage.tone]} ${
                active ? "ring-1 ring-current/30" : ""
              }`}
            >
              <div className="flex items-center justify-between">
                <p className="font-display text-base font-semibold text-fg">
                  {stage.title}
                </p>
                <span className="flex items-center gap-1.5 font-mono text-xs text-fg-muted">
                  {active && (
                    <span className="h-2 w-2 animate-pulse-soft rounded-full bg-gold" />
                  )}
                  {count}
                </span>
              </div>
              <p className="mt-0.5 font-mono text-[11px] uppercase tracking-widest text-fg-muted/70">
                {stage.tagline}
              </p>
              <p className="mt-2 text-sm text-fg-muted">{stage.blurb}</p>
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 rounded-card border border-line bg-ink-900 p-3 font-mono text-[11px] text-fg-muted">
        <span className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-gold" /> LLM + ML (reasoning only)
        </span>
        <span className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-rose" /> Hard safety gate
        </span>
        <span className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-mint" /> Money path (integer paise)
        </span>
      </div>

      {totalLive === 0 && (
        <Empty label="No cases in flight. Ingest events or run a recovery batch to see the pipeline light up." />
      )}
    </section>
  );
}
