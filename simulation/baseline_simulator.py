"""Simple one-retry baseline used to measure incremental recovery."""
from __future__ import annotations

import numpy as np

from simulation.evaluator import SimulationResult
from simulation.generator import EventRecord


class BaselineSimulator:
    RECOVERY_RATE = 0.154
    RETRY_COST_PAISE = 200
    LTV_SKIP_THRESHOLD_PAISE = 300_000
    AMOUNT_SKIP_THRESHOLD_PAISE = 50_000

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    def run(self, events: list[EventRecord]) -> SimulationResult:
        recovered = 0
        interventions = 0
        total_cost = 0
        breakdown = {"RETRY": {"attempts": 0, "recoveries": 0, "revenue_recovered_paise": 0, "cost_paise": 0}}
        for event in events:
            if event.customer_ltv_paise < self.LTV_SKIP_THRESHOLD_PAISE and event.transaction_amount_paise < self.AMOUNT_SKIP_THRESHOLD_PAISE:
                continue
            interventions += 1
            total_cost += self.RETRY_COST_PAISE
            breakdown["RETRY"]["attempts"] += 1
            if self.rng.random() < self.RECOVERY_RATE:
                recovered += event.transaction_amount_paise
                breakdown["RETRY"]["recoveries"] += 1
                breakdown["RETRY"]["revenue_recovered_paise"] += event.transaction_amount_paise
            breakdown["RETRY"]["cost_paise"] += self.RETRY_COST_PAISE
        at_risk = sum(event.transaction_amount_paise for event in events)
        return SimulationResult(
            total_events=len(events), total_revenue_at_risk_paise=at_risk,
            total_recovered_paise=recovered,
            recovery_rate=recovered / at_risk if at_risk else 0.0,
            total_interventions=interventions, total_discount_cost_paise=0,
            total_recovery_cost_paise=total_cost, net_recovered_paise=recovered - total_cost,
            strategy_breakdown=breakdown,
        )