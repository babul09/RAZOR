"use client";

import { useState } from "react";

import AgentActivitySection from "@/components/AgentActivitySection";
import CaseDrillDown from "@/components/CaseDrillDown";
import OverviewSection from "@/components/OverviewSection";
import RecoveryQueueSection from "@/components/RecoveryQueueSection";
import SimulationSection from "@/components/SimulationSection";
import StrategyPerformanceSection from "@/components/StrategyPerformanceSection";

type Tab = "overview" | "queue" | "activity" | "strategies" | "simulation";

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: "overview", label: "Overview", icon: "◈" },
  { id: "queue", label: "Recovery Queue", icon: "▤" },
  { id: "activity", label: "Agent Activity", icon: "◌" },
  { id: "strategies", label: "Strategy", icon: "≋" },
  { id: "simulation", label: "Simulation", icon: "▶" },
];

export default function Home() {
  const [tab, setTab] = useState<Tab>("overview");
  const [selectedCase, setSelectedCase] = useState<string | null>(null);

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      {/* Ops rail */}
      <aside className="shrink-0 border-b border-line bg-ink-900/60 md:w-56 md:border-b-0 md:border-r">
        <div className="flex items-center gap-2 px-5 py-4">
          <span className="grid h-8 w-8 place-items-center rounded-card bg-gold/15 font-display text-sm font-bold text-gold">
            R
          </span>
          <div className="leading-tight">
            <p className="font-display text-sm font-bold tracking-wide text-fg">RAZOR</p>
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-fg-muted">
              recovery terminal
            </p>
          </div>
        </div>

        <nav className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-col md:pb-0">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              aria-current={tab === t.id ? "page" : undefined}
              className={`flex shrink-0 items-center gap-2.5 rounded-card px-3 py-2 text-sm transition-colors md:w-full ${
                tab === t.id
                  ? "bg-ink-700 text-gold"
                  : "text-fg-muted hover:bg-ink-800 hover:text-fg"
              }`}
            >
              <span className="w-4 text-center font-mono text-xs" aria-hidden>
                {t.icon}
              </span>
              <span className="whitespace-nowrap">{t.label}</span>
            </button>
          ))}
        </nav>
      </aside>

      {/* Content */}
      <main className="min-w-0 flex-1 p-4 md:p-6">
        <div>
          {tab === "overview" && <OverviewSection />}
          {tab === "queue" && <RecoveryQueueSection onSelect={setSelectedCase} />}
          {tab === "activity" && <AgentActivitySection caseId={selectedCase || "case-1"} />}
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
