"use client";

import { useEffect, useState } from "react";

import { formatInr, getCaseDetail, type CaseDetail } from "@/lib/api";

export default function CaseDrillDown({
  caseId,
  onClose,
}: {
  caseId: string;
  onClose: () => void;
}) {
  const [detail, setDetail] = useState<CaseDetail | null>(null);

  useEffect(() => {
    getCaseDetail(caseId).then(setDetail);
  }, [caseId]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="max-h-[80vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white p-5 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Case {caseId.slice(0, 8)}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            ✕
          </button>
        </div>

        {detail && (
          <div className="mb-4 grid grid-cols-2 gap-3 text-sm">
            <Info label="Amount at risk" value={formatInr(detail.amount_at_risk_paise)} />
            <Info label="Status" value={detail.status} />
            <Info label="Failure code" value={detail.failure_code || "—"} />
            <Info label="Priority" value={String(detail.priority)} />
          </div>
        )}

        <h3 className="mb-2 text-sm font-semibold text-slate-700">Decision timeline & audit trail</h3>
        <ol className="space-y-3">
          {(detail?.timeline ?? []).map((entry, i) => {
            const isBlock =
              entry.event_type.includes("BLOCK") ||
              entry.event_type.includes("POLICY") ||
              entry.event_type.includes("APPROVAL");
            return (
              <li
                key={i}
                className={`rounded-lg border p-3 ${
                  isBlock ? "border-orange-200 bg-orange-50" : "border-slate-200 bg-white"
                }`}
              >
                <div className="flex items-center gap-2 text-xs text-slate-500">
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 font-medium">
                    {entry.event_type}
                  </span>
                  <span>{entry.created_at}</span>
                  {isBlock && <span className="font-medium text-orange-600">guardrail</span>}
                </div>
                <p className="mt-1 text-sm text-slate-700">
                  {entry.detail?.reasoning
                    ? String(entry.detail.reasoning)
                    : entry.detail?.reason
                      ? String(entry.detail.reason)
                      : JSON.stringify(entry.detail ?? {})}
                </p>
              </li>
            );
          })}
          {(detail?.timeline ?? []).length === 0 && (
            <li className="text-sm text-slate-400">No timeline entries</li>
          )}
        </ol>
      </div>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-slate-100 p-2">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="font-medium text-slate-700">{value}</p>
    </div>
  );
}
