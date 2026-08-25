"use client";

import { Fragment, useEffect, useMemo, useRef, useState } from "react";

import {
  explainCase,
  formatInr,
  getCaseDetail,
  getCases,
  type CaseDetail,
  type CaseSummary,
  type TimelineEntry,
} from "@/lib/api";
import { Empty, Loading } from "./State";

const STAGES = [
  { key: "ingest", title: "Ingest", desc: "event → case" },
  { key: "diagnose", title: "Diagnose", desc: "Gemini explains why" },
  { key: "strategy", title: "Strategy", desc: "ML picks the tactic" },
  { key: "policy", title: "Policy gate", desc: "guardrail check" },
  { key: "execute", title: "Execute", desc: "action → measured outcome" },
  { key: "learn", title: "Learn", desc: "memory + profile" },
];

const STATUS_STAGE: Record<string, number> = {
  NEW: 1,
  DIAGNOSING: 1,
  PREDICTED: 2,
  STRATEGY_SELECTED: 2,
  POLICY_CHECK: 3,
  AWAITING_APPROVAL: 3,
  EXECUTING: 4,
  VERIFYING: 4,
  RECOVERED: 5,
  FAILED: 5,
  STOPPED: 5,
};

/** Map a timeline event to the pipeline stage it belongs to. */
function stageOf(entry: TimelineEntry): number {
  const t = (entry.event_type || "").toUpperCase();
  if (t === "DIAGNOSIS") return 1;
  if (t === "DECISION" || t === "AGENT_DECISION") return 2;
  if (t.includes("POLICY") || t.includes("BLOCK") || t.includes("APPROVAL")) return 3;
  if (t === "OUTCOME") return 4;
  if (t === "EXPLANATION") return 5;
  return -1;
}

function stepText(entry: TimelineEntry): string {
  const d = entry.detail;
  if (!d) return "";
  if (typeof d.diagnosis === "string") return d.diagnosis;
  if (typeof d.reasoning === "string") return d.reasoning;
  if (typeof d.reason === "string") return d.reason;
  if (typeof d.explanation === "string") return d.explanation;
  if (d.selected_strategy) return `Selected ${d.selected_strategy}`;
  if (d.status === "RECOVERED" || d.status === "FAILED")
    return `Outcome: ${d.status} · ${formatInr(Number(d.revenue_recovered_paise ?? 0))} recovered · cost ${formatInr(Number(d.cost_paise ?? 0))}`;
  if (d.status) return `Policy: ${d.status}${d.reason ? ` — ${d.reason}` : ""}`;
  return JSON.stringify(d);
}

export default function RecoveryLabSection() {
  const [cases, setCases] = useState<CaseSummary[] | null>(null);
  const [caseId, setCaseId] = useState<string | null>(null);
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [explaining, setExplaining] = useState(false);
  const [explanation, setExplanation] = useState<{
    diagnosis: Record<string, unknown>;
    explanation: string;
  } | null>(null);

  // Step player state.
  const [reveal, setReveal] = useState(0);
  const [playing, setPlaying] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    getCases().then((c) => {
      setCases(c);
      if (c.length > 0 && !caseId) {
        setCaseId(c[0].id);
      }
    });
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const steps = useMemo(() => {
    if (!detail) return [];
    return [...detail.timeline].sort((a, b) =>
      (a.created_at || "").localeCompare(b.created_at || ""),
    );
  }, [detail]);

  useEffect(() => {
    if (!caseId) return;
    setLoadingDetail(true);
    setDetail(null);
    setExplanation(null);
    setReveal(0);
    setPlaying(false);
    if (timerRef.current) clearInterval(timerRef.current);
    getCaseDetail(caseId).then((d) => {
      setDetail(d);
      setLoadingDetail(false);
    });
  }, [caseId]);

  useEffect(() => {
    if (playing && reveal < steps.length) {
      timerRef.current = setInterval(() => {
        setReveal((r) => {
          if (r + 1 >= steps.length) {
            setPlaying(false);
            return steps.length;
          }
          return r + 1;
        });
      }, 1400);
      return () => {
        if (timerRef.current) clearInterval(timerRef.current);
      };
    }
    if (reveal >= steps.length) setPlaying(false);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [playing, reveal, steps.length]);

  const activeStage =
    reveal > 0 ? stageOf(steps[reveal - 1]) : STATUS_STAGE[detail?.status ?? ""] ?? -1;

  async function handleExplain() {
    if (!caseId) return;
    setExplaining(true);
    setExplanation(await explainCase(caseId));
    setExplaining(false);
  }

  if (cases === null) return <Loading label="Loading recovery cases" />;
  if (cases.length === 0)
    return <Empty label="No cases yet. Ingest events or run a recovery batch first." />;

  const selected = cases.find((c) => c.id === caseId);

  return (
    <section className="space-y-4">
      {/* Case selector + summary */}
      <div className="flex flex-wrap items-center gap-3 rounded-card border border-line bg-ink-900 p-3 shadow-card">
        <label className="font-mono text-xs uppercase tracking-wider text-fg-muted">
          Case
        </label>
        <select
          value={caseId ?? ""}
          onChange={(e) => setCaseId(e.target.value)}
          className="rounded border border-line bg-ink-800 px-3 py-1.5 font-mono text-sm text-fg focus:border-gold"
        >
          {cases.map((c) => (
            <option key={c.id} value={c.id}>
              {c.customer_id.slice(0, 8)} · {c.failure_code || "—"} · {formatInr(c.amount_at_risk_paise)}
            </option>
          ))}
        </select>
        {selected && (
          <div className="ml-auto flex flex-wrap gap-x-4 gap-y-1 font-mono text-xs text-fg-muted">
            <span>
              amount <span className="text-fg">{formatInr(selected.amount_at_risk_paise)}</span>
            </span>
            <span>
              issue <span className="text-fg">{selected.failure_code || "—"}</span>
            </span>
            <span>
              status <span className="text-gold">{selected.status}</span>
            </span>
          </div>
        )}
      </div>

      {loadingDetail ? (
        <Loading label="Loading case story" />
      ) : !detail ? null : (
        <>
          {/* Pipeline graph */}
          <div className="rounded-card border border-line bg-ink-900 p-5 shadow-card">
            <div className="flex items-center justify-between">
              <p className="font-mono text-eyebrow uppercase text-fg-muted">
                Recovery pipeline
              </p>
              <span className="font-mono text-[11px] text-fg-muted/70">
                {steps.length} steps · stage {Math.max(0, activeStage) + 1}/6
              </span>
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-y-2">
              {STAGES.map((s, i) => {
                const isActive = i === activeStage;
                const isDone = i < activeStage;
                return (
                  <Fragment key={s.key}>
                    {i > 0 && (
                      <span className="px-1 font-mono text-fg-muted/40" aria-hidden>
                        →
                      </span>
                    )}
                    <div
                      className={`flex items-center gap-2 rounded-full border px-3 py-1.5 transition-all ${
                        isActive
                          ? "border-gold/60 bg-gold/10 text-fg"
                          : isDone
                            ? "border-mint/40 text-fg-muted"
                            : "border-line text-fg-muted/70"
                      }`}
                    >
                      <span
                        className={`h-2 w-2 rounded-full ${
                          isActive ? "animate-pulse-soft bg-gold" : isDone ? "bg-mint" : "bg-ink-700"
                        }`}
                      />
                      <span className="font-mono text-[11px] uppercase tracking-wider">
                        {s.title}
                      </span>
                    </div>
                  </Fragment>
                );
              })}
            </div>
          </div>

          {/* Step-by-step player + Gemini explanation */}
          <div className="grid gap-4 lg:grid-cols-2">
            {/* Player */}
            <div className="rounded-card border border-line bg-ink-900 p-5 shadow-card">
              <div className="flex items-center justify-between">
                <p className="font-mono text-eyebrow uppercase text-fg-muted">
                  Step by step
                </p>
                <span className="font-mono text-[11px] text-fg-muted">
                  {reveal}/{steps.length}
                </span>
              </div>

              <div className="mt-3 flex gap-2">
                <button
                  onClick={() => {
                    setPlaying((p) => !p);
                    if (!playing && reveal >= steps.length) setReveal(0);
                  }}
                  disabled={steps.length === 0}
                  className="rounded-card bg-gold px-4 py-1.5 font-mono text-xs font-bold uppercase tracking-widest text-ink-950 transition-transform hover:-translate-y-0.5 disabled:opacity-40"
                >
                  {playing ? "Pause" : reveal >= steps.length ? "Replay" : "Play"}
                </button>
                <button
                  onClick={() => setReveal((r) => Math.min(steps.length, r + 1))}
                  disabled={playing || reveal >= steps.length}
                  className="rounded-card border border-line bg-ink-800 px-3 py-1.5 font-mono text-xs font-semibold uppercase tracking-widest text-fg transition-colors hover:bg-ink-700 disabled:opacity-40"
                >
                  Step
                </button>
                <button
                  onClick={() => {
                    setPlaying(false);
                    setReveal(0);
                  }}
                  disabled={reveal === 0}
                  className="rounded-card border border-line bg-ink-800 px-3 py-1.5 font-mono text-xs font-semibold uppercase tracking-widest text-fg-muted transition-colors hover:bg-ink-700 disabled:opacity-40"
                >
                  Reset
                </button>
              </div>

              <ol className="mt-4 space-y-2">
                {steps.slice(0, reveal).map((entry, i) => {
                  const stage = stageOf(entry);
                  const s = STAGES[Math.max(0, stage)];
                  return (
                    <li
                      key={i}
                      className="rounded-card border border-line bg-ink-800/60 p-3"
                    >
                      <div className="flex items-center gap-2">
                        <span className="rounded-full bg-gold/15 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-gold">
                          {s.title}
                        </span>
                        <span className="font-mono text-[10px] text-fg-muted">
                          {entry.created_at}
                        </span>
                      </div>
                      <p className="mt-1.5 text-sm text-fg">{stepText(entry)}</p>
                    </li>
                  );
                })}
                {reveal === 0 && (
                  <p className="py-6 text-center font-mono text-sm text-fg-muted">
                    Press Play or Step to walk through this case's recovery.
                  </p>
                )}
              </ol>
            </div>

            {/* Gemini explanation */}
            <div className="rounded-card border border-gold/30 bg-ink-900 p-5 shadow-card">
              <div className="flex items-center justify-between">
                <p className="font-mono text-eyebrow uppercase text-fg-muted">
                  Gemini explanation
                </p>
                <button
                  onClick={handleExplain}
                  disabled={explaining}
                  className="rounded-card border border-gold/40 bg-gold/10 px-3 py-1.5 font-mono text-[11px] font-semibold uppercase tracking-widest text-gold transition-colors hover:bg-gold/20 disabled:opacity-50"
                >
                  {explaining ? "Explaining…" : "Explain with Gemini"}
                </button>
              </div>

              {explaining ? (
                <div className="mt-4 space-y-2">
                  <div className="h-3 w-2/3 animate-pulse rounded-full bg-ink-700" />
                  <div className="h-3 w-full animate-pulse rounded-full bg-ink-700" />
                  <div className="h-3 w-5/6 animate-pulse rounded-full bg-ink-700" />
                </div>
              ) : explanation ? (
                <div className="mt-4">
                  {Boolean(explanation.diagnosis?.diagnosis) && (
                    <div className="rounded-card border border-line bg-ink-800/60 p-3">
                      <p className="font-mono text-[10px] uppercase tracking-wider text-fg-muted">
                        Diagnosis
                      </p>
                      <p className="mt-1 text-sm text-fg">
                        {String(explanation.diagnosis.diagnosis ?? "")}
                      </p>
                    </div>
                  )}
                  <div className="mt-3 rounded-card border border-gold/30 bg-ink-800/60 p-3">
                    <p className="font-mono text-[10px] uppercase tracking-wider text-gold">
                      Why this action
                    </p>
                    <p className="mt-1 text-sm leading-relaxed text-fg">
                      {explanation.explanation}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="mt-4">
                  {steps
                    .filter((e) => (e.event_type || "").toUpperCase() === "EXPLANATION")
                    .slice(0, 1)
                    .map((e, i) => (
                      <p key={i} className="rounded-card border border-line bg-ink-800/60 p-3 text-sm text-fg">
                        {stepText(e)}
                      </p>
                    ))}
                  {!steps.some((e) => (e.event_type || "").toUpperCase() === "EXPLANATION") && (
                    <p className="rounded-card border border-dashed border-line p-4 text-center font-mono text-sm text-fg-muted">
                      Tap <span className="text-gold">Explain with Gemini</span> to see the model
                      walk through why this case was handled the way it was.
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </section>
  );
}
