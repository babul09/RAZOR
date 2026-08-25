"use client";

import { useState } from "react";

import CaseDrillDown from "@/components/CaseDrillDown";
import CustomersSection from "@/components/CustomersSection";
import HowItWorksSection from "@/components/HowItWorksSection";
import OperatorSection from "@/components/OperatorSection";
import OverviewSection from "@/components/OverviewSection";
import RazorpaySection from "@/components/RazorpaySection";
import RecoveryLabSection from "@/components/RecoveryLabSection";
import RecoveryQueueSection from "@/components/RecoveryQueueSection";
import SimulationSection from "@/components/SimulationSection";
import StatusStrip from "@/components/StatusStrip";
import StrategyPerformanceSection from "@/components/StrategyPerformanceSection";

type Tab = "lab" | "how" | "overview" | "queue" | "operator" | "customers" | "strategies" | "simulation" | "razorpay";

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: "lab", label: "Recovery Lab", icon: "◉" },
  { id: "how", label: "How it works", icon: "◎" },
  { id: "overview", label: "Overview", icon: "◈" },
  { id: "queue", label: "Recovery Queue", icon: "▤" },
  { id: "operator", label: "Operator", icon: "⚙" },
  { id: "customers", label: "Customers", icon: "◍" },
  { id: "razorpay", label: "Razorpay", icon: "⛁" },
  { id: "strategies", label: "Strategy", icon: "≋" },
  { id: "simulation", label: "Simulation", icon: "▶" },
];

const TITLES: Record<Tab, { title: string; sub: string }> = {
  lab: { title: "Recovery Lab", sub: "Watch a case move through the pipeline, step by step" },
  how: { title: "How it works", sub: "What RAZOR does and why it works" },
  overview: { title: "Overview", sub: "Measured recovery across every event type" },
  queue: { title: "Recovery queue", sub: "Every revenue-at-risk case, prioritized" },
  operator: { title: "Operator", sub: "Payment limits, approvals, and manual actions" },
  customers: { title: "Customers", sub: "Search users and their recovery history" },
  razorpay: { title: "Razorpay live", sub: "Real failed payments · side-by-side recovery" },
  strategies: { title: "Strategy", sub: "What recovers money and what it costs" },
  simulation: { title: "Simulation", sub: "Project recovery across a synthetic batch" },
};

export default function Home() {
  const [tab, setTab] = useState<Tab>("lab");
  const [selectedCase, setSelectedCase] = useState<string | null>(null);
  const meta = TITLES[tab];

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      {/* Ops rail */}
      <aside className="shrink-0 border-b border-line bg-ink-900/80 md:w-60 md:border-b-0 md:border-r">
        <div className="flex items-center gap-3 px-5 py-4">
          <span className="grid h-9 w-9 place-items-center rounded-card bg-gold/15 font-display text-base font-bold text-gold">
            R
          </span>
          <div className="leading-tight">
            <p className="font-display text-sm font-bold tracking-wide text-fg">RAZOR</p>
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-fg-muted">
              revenue recovery
            </p>
          </div>
        </div>

        <nav className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-col md:pb-4">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              aria-current={tab === t.id ? "page" : undefined}
              className={`flex shrink-0 items-center gap-2.5 rounded-card px-3 py-2 text-sm transition-colors md:w-full ${
                tab === t.id
                  ? "bg-ink-700 text-fg"
                  : "text-fg-muted hover:bg-ink-700/60 hover:text-fg"
              }`}
            >
              <span className="w-4 text-center font-mono text-xs" aria-hidden>
                {t.icon}
              </span>
              <span className="whitespace-nowrap">{t.label}</span>
              {tab === t.id && (
                <span className="ml-auto hidden h-1.5 w-1.5 rounded-full bg-gold md:block" />
              )}
            </button>
          ))}
        </nav>
      </aside>

      {/* Content */}
      <main className="min-w-0 flex-1 p-4 md:p-6">
        <div className="mx-auto max-w-6xl space-y-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <div>
              <h1 className="font-display text-xl font-bold text-fg">{meta.title}</h1>
              <p className="font-mono text-xs text-fg-muted">{meta.sub}</p>
            </div>
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-fg-muted">
              RAZOR · recovery terminal
            </p>
          </div>

          <StatusStrip />

          {tab === "lab" && <RecoveryLabSection />}
          {tab === "how" && <HowItWorksSection />}
          {tab === "overview" && <OverviewSection />}
          {tab === "queue" && <RecoveryQueueSection onSelect={setSelectedCase} />}
          {tab === "operator" && <OperatorSection />}
          {tab === "customers" && <CustomersSection />}
          {tab === "razorpay" && <RazorpaySection />}
          {tab === "strategies" && <StrategyPerformanceSection />}
          {tab === "simulation" && <SimulationSection />}
        </div>
      </main>

      {selectedCase && (
        <CaseDrillDown caseId={selectedCase} onClose={() => setSelectedCase(null)} />
      )}
    </div>
  );
}
