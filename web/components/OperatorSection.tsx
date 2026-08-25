"use client";

import { useCallback, useEffect, useState } from "react";

import {
  approveCase,
  CHOOSABLE_STRATEGIES,
  formatInr,
  getCases,
  getPolicy,
  rejectCase,
  takeAction,
  updatePolicy,
  type ActionResult,
  type CaseSummary,
  type Policy,
} from "@/lib/api";
import { Empty, Loading } from "./State";

const ACTIONABLE = ["NEW", "DIAGNOSING", "PREDICTED", "STRATEGY_SELECTED"];

export default function OperatorSection() {
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [cases, setCases] = useState<CaseSummary[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  // Policy form (rupee inputs, stored as paise).
  const [maxAuto, setMaxAuto] = useState("");
  const [approvalAbove, setApprovalAbove] = useState("");
  const [maxDiscount, setMaxDiscount] = useState("");
  const [maxContacts, setMaxContacts] = useState("");

  const load = useCallback(() => {
    getPolicy().then((p) => {
      setPolicy(p);
      setMaxAuto(String(Math.round(p.max_automated_amount_paise / 100)));
      setApprovalAbove(String(Math.round(p.require_human_approval_above_paise / 100)));
      setMaxDiscount(String(p.max_discount_percent));
      setMaxContacts(String(p.max_contacts_count));
    });
    getCases().then(setCases);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const flash = (kind: "ok" | "err", text: string) => {
    setMsg({ kind, text });
    setTimeout(() => setMsg(null), 4000);
  };

  async function handleSavePolicy() {
    setBusy(true);
    try {
      await updatePolicy({
        max_automated_amount_paise: Math.round(Number(maxAuto) * 100),
        require_human_approval_above_paise: Math.round(Number(approvalAbove) * 100),
        max_discount_percent: Number(maxDiscount),
        max_contacts_count: Number(maxContacts),
      });
      flash("ok", "Payment limits saved.");
      load();
    } catch (e) {
      flash("err", e instanceof Error ? e.message : "Could not save limits");
    } finally {
      setBusy(false);
    }
  }

  async function run(fn: () => Promise<ActionResult>, okText: string) {
    setBusy(true);
    try {
      const r = await fn();
      if (r.executed) flash("ok", `${okText} → ${r.status}${r.recovered ? " · recovered" : ""}`);
      else if (r.policy && r.policy !== "PASS")
        flash("err", `${r.policy} — ${r.reason ?? "policy gate"}`);
      else flash("ok", okText);
    } catch (e) {
      flash("err", e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy(false);
      load();
    }
  }

  if (policy === null || cases === null) return <Loading label="Loading operator console" />;

  const pendingApprovals = cases.filter((c) => c.status === "AWAITING_APPROVAL");
  const actionable = cases.filter((c) => ACTIONABLE.includes(c.status));

  const field = "rounded border border-line bg-ink-800 px-3 py-1.5 font-mono text-sm text-fg focus:border-gold";

  return (
    <section className="space-y-4">
      {/* Payment limits */}
      <div className="rounded-card border border-line bg-ink-900 p-5 shadow-card">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-mono text-eyebrow uppercase text-fg-muted">
              Payment limits · policy guardrails
            </p>
            <p className="mt-1 font-mono text-[11px] text-fg-muted/70">
              These are hard gates — no action bypasses them.
            </p>
          </div>
        </div>

        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Field label="Max automated amount" unit="₹">
            <input type="number" value={maxAuto} onChange={(e) => setMaxAuto(e.target.value)} className={field} />
          </Field>
          <Field label="Human approval above" unit="₹">
            <input type="number" value={approvalAbove} onChange={(e) => setApprovalAbove(e.target.value)} className={field} />
          </Field>
          <Field label="Max discount" unit="%">
            <input type="number" value={maxDiscount} onChange={(e) => setMaxDiscount(e.target.value)} className={field} />
          </Field>
          <Field label="Max contacts" unit="">
            <input type="number" value={maxContacts} onChange={(e) => setMaxContacts(e.target.value)} className={field} />
          </Field>
        </div>

        <div className="mt-4 flex items-center gap-3">
          <button
            onClick={handleSavePolicy}
            disabled={busy}
            className="rounded-card bg-gold px-4 py-2 font-mono text-xs font-bold uppercase tracking-widest text-ink-950 transition-transform hover:-translate-y-0.5 disabled:opacity-50"
          >
            Save limits
          </button>
          {msg && (
            <span className={`font-mono text-xs ${msg.kind === "ok" ? "text-mint" : "text-rose"}`}>
              {msg.text}
            </span>
          )}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Pending approvals */}
        <div className="rounded-card border border-line bg-ink-900 p-5 shadow-card">
          <p className="font-mono text-eyebrow uppercase text-fg-muted">
            Pending approvals · {pendingApprovals.length}
          </p>
          {pendingApprovals.length === 0 ? (
            <Empty label="No cases awaiting approval." />
          ) : (
            <ul className="mt-3 space-y-2">
              {pendingApprovals.map((c) => (
                <li key={c.id} className="rounded-card border border-line bg-ink-800/60 p-3">
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
                    <span className="font-mono text-xs text-fg-muted">{c.customer_id.slice(0, 8)}</span>
                    <span className="money text-sm text-gold">{formatInr(c.amount_at_risk_paise)}</span>
                    <span className="font-mono text-xs text-fg-muted">{c.failure_code || "—"}</span>
                    <div className="ml-auto flex gap-2">
                      <button
                        onClick={() => run(() => approveCase(c.id), "Approved")}
                        disabled={busy}
                        className="rounded-card bg-mint px-3 py-1 font-mono text-xs font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => run(() => rejectCase(c.id), "Rejected")}
                        disabled={busy}
                        className="rounded-card border border-rose/40 bg-rose/10 px-3 py-1 font-mono text-xs font-semibold text-rose transition-colors hover:bg-rose/20 disabled:opacity-50"
                      >
                        Reject
                      </button>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Choose an action */}
        <div className="rounded-card border border-line bg-ink-900 p-5 shadow-card">
          <p className="font-mono text-eyebrow uppercase text-fg-muted">
            Choose an action · {actionable.length}
          </p>
          {actionable.length === 0 ? (
            <Empty label="No decision-pending cases right now." />
          ) : (
            <ul className="mt-3 space-y-2">
              {actionable.map((c) => (
                <ActionRow
                  key={c.id}
                  caseId={c.id}
                  customer={c.customer_id}
                  amount={c.amount_at_risk_paise}
                  issue={c.failure_code}
                  busy={busy}
                  onRun={(strategy) =>
                    run(() => takeAction(c.id, strategy), `Executed ${strategy}`)
                  }
                />
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}

function Field({
  label,
  unit,
  children,
}: {
  label: string;
  unit: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="font-mono text-[11px] uppercase tracking-wider text-fg-muted">
        {label} {unit && <span className="text-fg-muted/60">({unit})</span>}
      </span>
      <div className="mt-1">{children}</div>
    </label>
  );
}

function ActionRow({
  caseId,
  customer,
  amount,
  issue,
  busy,
  onRun,
}: {
  caseId: string;
  customer: string;
  amount: number;
  issue: string | null;
  busy: boolean;
  onRun: (strategy: string) => void;
}) {
  const [strategy, setStrategy] = useState("RETRY");
  return (
    <li className="rounded-card border border-line bg-ink-800/60 p-3">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <span className="font-mono text-xs text-fg-muted">{customer.slice(0, 8)}</span>
        <span className="money text-sm text-gold">{formatInr(amount)}</span>
        <span className="font-mono text-xs text-fg-muted">{issue || "—"}</span>
        <div className="ml-auto flex items-center gap-2">
          <select
            value={strategy}
            onChange={(e) => setStrategy(e.target.value)}
            disabled={busy}
            className="rounded border border-line bg-ink-800 px-2 py-1 font-mono text-xs text-fg focus:border-gold disabled:opacity-50"
          >
            {CHOOSABLE_STRATEGIES.map((s) => (
              <option key={s} value={s}>
                {s.replace(/_/g, " ")}
              </option>
            ))}
          </select>
          <button
            onClick={() => onRun(strategy)}
            disabled={busy}
            className="rounded-card bg-gold px-3 py-1 font-mono text-xs font-bold text-ink-950 transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            Execute
          </button>
        </div>
      </div>
    </li>
  );
}
