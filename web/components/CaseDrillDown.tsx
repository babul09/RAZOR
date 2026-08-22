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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink-950/80 p-4 backdrop-blur-sm">
      <div className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-card border border-line bg-ink-900 p-5 shadow-card">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-display text-lg font-semibold text-fg">
            Case {caseId.slice(0, 8)}
          </h2>
          <button
            onClick={onClose}
            aria-label="Close"
            className="grid h-8 w-8 place-items-center rounded-card border border-line text-fg-muted transition-colors hover:border-gold hover:text-gold"
          >
            ✕
          </button>
        </div>

        {detail && (
          <div className="mb-4 grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
            <Info label="Amount at risk" value={formatInr(detail.amount_at_risk_paise)} accent="text-gold" />
            <Info label="Status" value={detail.status} />
            <Info label="Failure code" value={detail.failure_code || "—"} />
            <Info label="Priority" value={String(detail.priority)} />
          </div>
        )}

        <p className="mb-2 font-mono text-eyebrow uppercase text-fg-muted">
          Decision timeline · audit trail
        </p>
        <ol className="space-y-3">
          {(detail?.timeline ?? []).map((entry, i) => {
            const isBlock =
              entry.event_type.includes("BLOCK") ||
              entry.event_type.includes("POLICY") ||
              entry.event_type.includes("APPROVAL");
            return (
              <li
                key={i}
                className={`rounded-card border p-3 ${
                  isBlock ? "border-rose/30 bg-rose/5" : "border-line bg-ink-800/40"
                }`}
              >
                <div className="flex items-center gap-2 font-mono text-[11px] text-fg-muted">
                  <span
                    className={`rounded-full px-2 py-0.5 font-medium uppercase tracking-wide ${
                      isBlock ? "bg-rose/15 text-rose" : "bg-ink-700 text-fg-muted"
                    }`}
                  >
                    {entry.event_type}
                  </span>
                  <span>{entry.created_at}</span>
                  {isBlock && <span className="text-rose">guardrail</span>}
                </div>
                <p className="mt-1.5 text-sm text-fg">
                  {entry.detail?.reasoning
                    ? String(entry.detail.reasoning)
                    : entry.detail?.reason
                      ? String(entry.detail.reason)
                      : entry.detail?.diagnosis
                        ? String(entry.detail.diagnosis)
                        : JSON.stringify(entry.detail ?? {})}
                </p>
              </li>
            );
          })}
          {(detail?.timeline ?? []).length === 0 && (
            <li className="font-mono text-sm text-fg-muted">No timeline entries</li>
          )}
        </ol>
      </div>
    </div>
  );
}

function Info({
  label,
  value,
  accent = "text-fg",
}: {
  label: string;
  value: string;
  accent?: string;
}) {
  return (
    <div className="rounded-card border border-line bg-ink-800/40 p-2">
      <p className="font-mono text-[10px] uppercase tracking-wider text-fg-muted">{label}</p>
      <p className={`money mt-0.5 text-sm font-medium ${accent}`}>{value}</p>
    </div>
  );
}
