"use client";

/** Hero landing that explains what RAZOR does and how it works. */

const STEPS = [
  {
    n: "01",
    title: "Every failed payment is a case",
    body: "payment.failed, checkout.abandoned, subscription.failed and invoice.overdue land as revenue-at-risk cases. RAZOR scores each by amount × severity × recovery likelihood × customer value, so a ₹50,000 customer is never blocked behind a ₹500 one.",
  },
  {
    n: "02",
    title: "The agents diagnose, not execute",
    body: "A Gemini LLM explains why a payment failed and recommends timing. It only reasons — it never touches money. All arithmetic stays in integer paise, and the LLM is never in the critical payment path.",
  },
  {
    n: "03",
    title: "ML picks the right tactic",
    body: "The model predicts P(recovery) for every strategy — retry, UPI switch, WhatsApp, email, discount, human escalation. It picks the one with the best expected net recovery, and honestly says WAIT (better later) or STOP (not worth it).",
  },
  {
    n: "04",
    title: "Policy is a hard gate",
    body: "Before any action, guardrails check discount caps, contact limits, channel allow-lists and human-approval thresholds. A block routes to human review and is always audited — no exception bypasses the policy engine.",
  },
  {
    n: "05",
    title: "Execute, then measure",
    body: "The recovery action runs and its outcome is recorded — money recovered, cost, net — traced to that executed case. The dashboard headline reads these executed outcomes, not a projection.",
  },
  {
    n: "06",
    title: "It learns",
    body: "Every resolved case writes a (customer, failure, strategy, outcome) tuple. Customer profiles and per-channel success rates update, so the next recovery for the same customer starts smarter. A/B experiments tune strategy weights.",
  },
];

export default function HowItWorksSection() {
  return (
    <section className="space-y-6">
      {/* Hero */}
      <div className="rounded-card border border-gold/30 bg-ink-900 p-6 shadow-card">
        <p className="font-mono text-eyebrow uppercase tracking-[0.25em] text-gold">
          RAZOR · Revenue AI — Zero-loss Operations &amp; Recovery
        </p>
        <h1 className="mt-3 font-display text-3xl font-bold leading-tight text-fg md:text-4xl">
          Recover the revenue{" "}
          <span className="text-gold">every failed payment</span> is silently
          costing you.
        </h1>
        <p className="mt-4 max-w-3xl text-lg leading-relaxed text-fg-muted">
          RAZOR turns a payment-failure event into an autonomous, policy-guarded
          recovery operation: diagnose why it failed, score every recovery tactic
          with ML, enforce hard guardrails, execute the winning action, and
          measure the money actually recovered — then learn from every outcome.
        </p>
        <div className="mt-5 flex flex-wrap gap-3 font-mono text-xs text-fg-muted">
          <span className="rounded-full border border-line px-3 py-1">LLM diagnosis · never money</span>
          <span className="rounded-full border border-line px-3 py-1">Policy is a hard gate</span>
          <span className="rounded-full border border-line px-3 py-1">Integer-paise money</span>
          <span className="rounded-full border border-line px-3 py-1">Self-optimising via A/B</span>
        </div>
      </div>

      {/* The flow */}
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {STEPS.map((s) => (
          <div key={s.n} className="rounded-card border border-line bg-ink-900 p-5 shadow-card">
            <p className="font-mono text-xs tracking-widest text-gold">{s.n}</p>
            <h3 className="mt-1 font-display text-lg font-semibold text-fg">{s.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-fg-muted">{s.body}</p>
          </div>
        ))}
      </div>

      {/* Safety callout */}
      <div className="rounded-card border border-rose/30 bg-rose/5 p-5">
        <p className="font-mono text-eyebrow uppercase text-rose">Safety by design</p>
        <p className="mt-2 max-w-4xl text-sm leading-relaxed text-fg">
          The LLM and ML model only recommend. The policy engine is a hard gate
          that always runs before any action, and no agent ever executes a
          payment or performs money arithmetic. Recovery money is measured from
          executed outcomes, keeping the numbers honest.
        </p>
      </div>
    </section>
  );
}
