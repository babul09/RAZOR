"use client";

import { useState } from "react";

import AgentActivitySection from "@/components/AgentActivitySection";
import CaseDrillDown from "@/components/CaseDrillDown";
import OverviewSection from "@/components/OverviewSection";
import RecoveryQueueSection from "@/components/RecoveryQueueSection";
import SimulationSection from "@/components/SimulationSection";
import StrategyPerformanceSection from "@/components/StrategyPerformanceSection";

type Tab = "overview" | "queue" | "activity" | "strategies" | "simulation";

const TABS: { id: Tab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "queue", label: "Live Recovery Queue" },
  { id: "activity", label: "Agent Activity" },
  { id: "strategies", label: "Strategy Performance" },
  { id: "simulation", label: "Simulation" },
];

export default function Home() {
  const [tab, setTab] = useState<Tab>("overview");
  const [selectedCase, setSelectedCase] = useState<string | null>(null);

  return (
    <main className="mx-auto max-w-6xl p-6">
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-brand">RAZOR Dashboard</h1>
        <p className="text-sm text-slate-500">Revenue AI recovery operations</p>
      </header>

      <nav className="mb-6 flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`rounded-full px-4 py-1.5 text-sm font-medium ${
              tab === t.id
                ? "bg-brand text-white"
                : "bg-white text-slate-600 hover:bg-slate-50"
            } border border-slate-200`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <div>
        {tab === "overview" && <OverviewSection />}
        {tab === "queue" && <RecoveryQueueSection onSelect={setSelectedCase} />}
        {tab === "activity" && (
          <AgentActivitySection caseId={selectedCase || "case-1"} />
        )}
        {tab === "strategies" && <StrategyPerformanceSection />}
        {tab === "simulation" && <SimulationSection />}
      </div>

      {selectedCase && (
        <CaseDrillDown caseId={selectedCase} onClose={() => setSelectedCase(null)} />
      )}
    </main>
  );
}
