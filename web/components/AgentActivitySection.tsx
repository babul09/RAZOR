"use client";

import { useEffect, useState } from "react";

import { formatInr, getCaseDetail, type CaseDetail } from "@/lib/api";
import { Empty, Loading } from "./State";

export default function AgentActivitySection({ caseId }: { caseId: string }) {
  const [detail, setDetail] = useState<CaseDetail | null>(null);

  useEffect(() => {
    getCaseDetail(caseId).then(setDetail);
  }, [caseId]);

  if (!detail) return <Loading label="Loading timeline" />;
  if (detail.timeline.length === 0)
    return <Empty label="No timeline entries for this case." />;

  return (
    <section className="space-y-3">
      <p className="font-mono text-eyebrow uppercase text-fg-muted">
        Agent activity · case {detail.id.slice(0, 8)}
      </p>
      <ol className="space-y-3">
        {detail.timeline.map((entry, i) => {
          const isBlock =
            entry.event_type.includes("BLOCK") ||
            entry.event_type.includes("POLICY") ||
            entry.event_type.includes("APPROVAL");
          const isDecision = entry.type === "decision";
          return (
            <li
              key={i}
              className={`rounded-card border p-3 shadow-card ${
                isBlock
                  ? "border-rose/30 bg-rose/5"
                  : isDecision
                    ? "border-line bg-ink-800/40"
                    : "border-line bg-ink-900"
              }`}
            >
              <div className="flex items-center gap-2 font-mono text-[11px] text-fg-muted">
                <span
                  className={`rounded-full px-2 py-0.5 font-medium uppercase tracking-wide ${
                    isBlock
                      ? "bg-rose/15 text-rose"
                      : isDecision
                        ? "bg-gold/15 text-gold"
                        : "bg-ink-700 text-fg-muted"
                  }`}
                >
                  {entry.event_type}
                </span>
                <span>{entry.created_at}</span>
                {isBlock && <span className="text-rose">guardrail</span>}
              </div>
              <p className="mt-1.5 text-sm text-fg">
                {typeof entry.detail?.reasoning === "string"
                  ? entry.detail.reasoning
                  : entry.detail?.reason
                    ? String(entry.detail.reason)
                    : entry.detail?.diagnosis
                      ? String(entry.detail.diagnosis)
                      : entry.detail?.selected_strategy
                        ? `Selected ${entry.detail.selected_strategy}`
                        : entry.detail?.status
                          ? `Policy: ${entry.detail.status}`
                          : JSON.stringify(entry.detail ?? {})}
              </p>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
