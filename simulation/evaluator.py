"""Results, formatting, and persistence helpers for simulation runs."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class SimulationResult:
    total_events: int
    total_revenue_at_risk_paise: int
    total_recovered_paise: int
    recovery_rate: float
    total_interventions: int
    total_discount_cost_paise: int
    total_recovery_cost_paise: int
    net_recovered_paise: int
    strategy_breakdown: dict[str, dict]


def format_inr(paise: int) -> str:
    rupees = paise / 100
    if rupees >= 100_000:
        return f"₹{rupees / 100_000:.2f}L"
    return f"₹{rupees:,.0f}"


def print_comparison_table(baseline: SimulationResult, razor: SimulationResult) -> None:
    rows = [
        ("Revenue at risk", format_inr(baseline.total_revenue_at_risk_paise), format_inr(razor.total_revenue_at_risk_paise)),
        ("Revenue recovered", format_inr(baseline.total_recovered_paise), format_inr(razor.total_recovered_paise)),
        ("Recovery rate", f"{baseline.recovery_rate:.1%}", f"{razor.recovery_rate:.1%}"),
        ("Total interventions", f"{baseline.total_interventions:,}", f"{razor.total_interventions:,}"),
        ("Discount cost", format_inr(baseline.total_discount_cost_paise), format_inr(razor.total_discount_cost_paise)),
        ("Net revenue recovered", format_inr(baseline.net_recovered_paise), format_inr(razor.net_recovered_paise)),
    ]
    print("\nRAZOR SIMULATION RESULTS")
    print("=" * 62)
    print(f"{'Metric':<28} {'Baseline':>14} {'RAZOR':>14}")
    print("-" * 62)
    for label, baseline_value, razor_value in rows:
        print(f"{label:<28} {baseline_value:>14} {razor_value:>14}")
    incremental = razor.net_recovered_paise - baseline.net_recovered_paise
    print("-" * 62)
    print(f"{'INCREMENTAL REVENUE':<28} {'':>14} {('+' + format_inr(incremental)):>14}")
    print("=" * 62)


def print_strategy_breakdown(razor: SimulationResult) -> None:
    print("\nSTRATEGY BREAKDOWN")
    print("=" * 76)
    print(f"{'Strategy':<26} {'Attempts':>10} {'Recoveries':>11} {'Recovered':>14} {'Cost':>12}")
    print("-" * 76)
    for strategy, stats in razor.strategy_breakdown.items():
        print(
            f"{strategy:<26} {stats['attempts']:>10,} {stats['recoveries']:>11,} "
            f"{format_inr(stats['revenue_recovered_paise']):>14} "
            f"{format_inr(stats['cost_paise']):>12}"
        )
    print("=" * 76)


def save_results(baseline: SimulationResult, razor: SimulationResult, path: str) -> None:
    output = {"baseline": asdict(baseline), "razor": asdict(razor)}
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2), encoding="utf-8")