"use client";

import { useEffect, useState } from "react";

import { formatInr, formatInrSigned, getOverview, type Overview } from "@/lib/api";

/** Slim live ops strip across the top of the console. */
export default function StatusStrip() {
  const [data, setData] = useState<Overview | null>(null);

  useEffect(() => {
    let active = true;
    const load = () =>
      getOverview().then((o) => active && setData(o));
    load();
    const timer = setInterval(load, 4000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  const hasMeasured = data?.incremental_paise != null;
  const positive = (data?.incremental_paise ?? 0) >= 0;

  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-2 rounded-card border border-line bg-ink-900 px-4 py-2.5 shadow-card">
      <span className="flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-widest text-mint">
        <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-mint" />
        Live
      </span>

      <StripItem label="Incremental">
        <span className={hasMeasured ? (positive ? "text-mint" : "text-rose") : "text-fg-muted"}>
          {hasMeasured ? formatInrSigned(data!.incremental_paise!) : "—"}
        </span>
      </StripItem>
      <StripItem label="Recovered">
        <span className="text-fg">{formatInr(data?.recovered_paise ?? 0)}</span>
      </StripItem>
      <StripItem label="At risk">
        <span className="text-fg">{formatInr(data?.revenue_at_risk_paise ?? 0)}</span>
      </StripItem>
      <StripItem label="Rate">
        <span className="text-gold">
          {data ? `${(data.recovery_rate * 100).toFixed(1)}%` : "—"}
        </span>
      </StripItem>
      <StripItem label="Cases">
        <span className="text-fg">{data?.total_cases.toLocaleString() ?? "—"}</span>
      </StripItem>
    </div>
  );
}

function StripItem({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <span className="flex items-baseline gap-1.5 font-mono text-xs">
      <span className="uppercase tracking-wider text-fg-muted">{label}</span>
      <span className="money">{children}</span>
    </span>
  );
}
