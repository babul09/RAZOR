#!/usr/bin/env python3
"""RAZOR Revenue Recovery Simulator."""
from __future__ import annotations

import argparse

from simulation.baseline_simulator import BaselineSimulator
from simulation.evaluator import print_comparison_table, print_strategy_breakdown, save_results
from simulation.generator import SyntheticDataGenerator
from simulation.razor_simulator import RazorSimulator


def main() -> None:
    parser = argparse.ArgumentParser(description="RAZOR Revenue Recovery Simulator")
    parser.add_argument("--events", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--hour", type=int, default=14, choices=range(24))
    args = parser.parse_args()

    print(f"[RAZOR] Generating {args.events:,} events (seed={args.seed})...")
    dataset = SyntheticDataGenerator(seed=args.seed).generate(args.events)
    print("[RAZOR] Running baseline simulation...")
    baseline = BaselineSimulator(seed=args.seed).run(dataset.events)
    print(f"[RAZOR] Running RAZOR simulation (simulated hour: {args.hour}:00)...")
    razor = RazorSimulator(seed=args.seed).run(dataset.events, current_hour=args.hour)
    print_comparison_table(baseline, razor)
    print_strategy_breakdown(razor)
    save_results(baseline, razor, "simulation/data/results_latest.json")
    print("\n[RAZOR] Results saved to simulation/data/results_latest.json")


if __name__ == "__main__":
    main()