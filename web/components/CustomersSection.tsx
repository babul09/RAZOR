"use client";

import { useEffect, useRef, useState } from "react";

import {
  formatInr,
  searchCustomers,
  type CustomerSearchHit,
} from "@/lib/api";
import { Empty } from "./State";

const SEGMENT_STYLE: Record<string, string> = {
  A: "bg-gold/15 text-gold",
  B: "bg-mint/15 text-mint",
  C: "bg-blue-500/15 text-blue-700",
  D: "bg-rose/15 text-rose",
  E: "bg-ink-700 text-fg-muted",
};

const STATUS_STYLE: Record<string, string> = {
  RECOVERED: "bg-mint/15 text-mint",
  FAILED: "bg-rose/15 text-rose",
  AWAITING_APPROVAL: "bg-orange-500/15 text-orange-700",
  STRATEGY_SELECTED: "bg-gold/15 text-gold",
  STOPPED: "bg-ink-700 text-fg-muted",
};

export default function CustomersSection() {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<CustomerSearchHit[] | null>(null);
  const [searching, setSearching] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  function run(q: string) {
    setSearching(true);
    searchCustomers(q).then((h) => {
      setHits(h);
      setSearching(false);
    });
  }

  useEffect(() => {
    // Debounced search on type.
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => run(query), 350);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [query]);

  return (
    <section className="space-y-4">
      <div className="rounded-card border border-line bg-ink-900 p-4 shadow-card">
        <label className="font-mono text-eyebrow uppercase text-fg-muted">
          Search customers
        </label>
        <div className="mt-2 flex items-center gap-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by name, email, phone, or id…"
            className="w-full rounded border border-line bg-ink-800 px-3 py-2 font-mono text-sm text-fg placeholder:text-fg-muted/60 focus:border-gold"
          />
          {searching && (
            <span className="animate-pulse-soft font-mono text-xs text-fg-muted">searching…</span>
          )}
        </div>
        <p className="mt-2 font-mono text-[11px] text-fg-muted/70">
          {hits !== null ? `${hits.length} customers` : " "}
        </p>
      </div>

      {hits === null ? null : hits.length === 0 ? (
        <Empty label="No customers match your search." />
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {hits.map((c) => (
            <div key={c.id} className="rounded-card border border-line bg-ink-900 p-4 shadow-card">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate font-display text-base font-semibold text-fg">
                    {c.name}
                  </p>
                  <p className="font-mono text-[11px] text-fg-muted">
                    {c.email || "no email"} {c.phone ? `· ${c.phone}` : ""}
                  </p>
                </div>
                {c.segment && (
                  <span
                    className={`rounded-full px-2 py-0.5 font-mono text-[10px] uppercase ${
                      SEGMENT_STYLE[c.segment] || "bg-ink-700 text-fg-muted"
                    }`}
                  >
                    seg {c.segment}
                  </span>
                )}
              </div>

              <div className="mt-3 grid grid-cols-3 gap-2 font-mono text-xs">
                <Metric label="Lifetime" value={formatInr(c.lifetime_value_paise)} />
                <Metric label="At risk" value={formatInr(c.at_risk_paise)} />
                <Metric label="Recovered" value={formatInr(c.recovered_paise)} accent="text-mint" />
              </div>

              {c.cases.length > 0 && (
                <ul className="mt-3 space-y-1.5 border-t border-line pt-3">
                  {c.cases.slice(0, 4).map((case_) => (
                    <li key={case_.id} className="flex items-center gap-2">
                      <span className="font-mono text-[10px] text-fg-muted">
                        {case_.id.slice(-8)}
                      </span>
                      <span className="money text-xs text-fg">{formatInr(case_.amount_at_risk_paise)}</span>
                      <span className="font-mono text-[11px] text-fg-muted">
                        {case_.failure_code || "—"}
                      </span>
                      <span
                        className={`ml-auto rounded-full px-2 py-0.5 font-mono text-[10px] ${
                          STATUS_STYLE[case_.status ?? ""] || "bg-ink-700 text-fg-muted"
                        }`}
                      >
                        {case_.status}
                      </span>
                    </li>
                  ))}
                  {c.cases.length > 4 && (
                    <li className="font-mono text-[11px] text-fg-muted">
                      +{c.cases.length - 4} more case(s)
                    </li>
                  )}
                </ul>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function Metric({ label, value, accent = "text-fg" }: { label: string; value: string; accent?: string }) {
  return (
    <div className="rounded-card border border-line bg-ink-800/50 p-2">
      <p className="font-mono text-[9px] uppercase tracking-wider text-fg-muted">{label}</p>
      <p className={`money text-sm ${accent}`}>{value}</p>
    </div>
  );
}
