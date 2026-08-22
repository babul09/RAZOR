"use client";

import { useEffect, useState } from "react";

import { getCaseDetail, type CaseDetail } from "@/lib/api";
import { Empty, Loading } from "./State";

export default function AgentActivitySection({ caseId }: { caseId: string }) {
  const [detail, setDetail] = useState<CaseDetail | null>(null);

  useEffect(() => {
    getCaseDetail(caseId).then(setDetail);
  }, [caseId]);

  if (!detail) return <Loading label="Loading timeline…" />;
  if (detail.timeline.length === 0) return <Empty label="No timeline entries for this case." />;

  return (
    <section className="space-y-2">
      <p className="text-xs text-slate-500">Decision timeline for case {detail.id.slice(0, 8)}</p>
      <ol className="space-y-3">
        {detail.timeline.map((entry, i) => (
          <li key={i} className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span
                className={`rounded-full px-2 py-0.5 font-medium ${
                  entry.type === "decision"
                    ? "bg-indigo-100 text-indigo-700"
                    : entry.event_type.includes("BLOCK") || entry.event_type.includes("POLICY")
                      ? "bg-orange-100 text-orange-700"
                      : "bg-slate-100 text-slate-600"
                }`}
              >
                {entry.event_type}
              </span>
              <span>{entry.created_at}</span>
            </div>
            <p className="mt-1 text-sm text-slate-700">
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
        ))}
      </ol>
    </section>
  );
}
