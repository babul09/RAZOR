"""Deterministic strategy selection with stochastic, seeded outcomes."""
from __future__ import annotations

import numpy as np

from db.models import RecoveryStrategy
from simulation.evaluator import SimulationResult
from simulation.generator import EventRecord

RECOVERY_PROBS = {
    ("A", "RETRY", True): 0.78, ("A", "RETRY", False): 0.32, ("A", "WAIT", None): 0.78,
    ("B", "PAYMENT_METHOD_SWITCH", None): 0.81, ("B", "RETRY", None): 0.40,
    ("C", "WHATSAPP_REMINDER", None): 0.67, ("C", "EMAIL_REMINDER", None): 0.35,
    ("D", "HUMAN_ESCALATION", None): 0.85, ("D", "RETRY", None): 0.05,
    ("E", None, None): 0.05, ("default", None, None): 0.40,
}

STRATEGY_COSTS_PAISE = {
    "RETRY": 200, "PAYMENT_METHOD_SWITCH": 300, "WHATSAPP_REMINDER": 100,
    "EMAIL_REMINDER": 50, "PAYMENT_LINK": 0, "DISCOUNT_OFFER": None,
    "HUMAN_ESCALATION": 25_000, "WAIT": 0, "STOP": 0,
}


def select_strategy(event: EventRecord, current_hour: int) -> RecoveryStrategy:
    if event.segment == "E":
        return RecoveryStrategy.STOP
    if event.segment == "D" and event.transaction_amount_paise > 500_000:
        return RecoveryStrategy.HUMAN_ESCALATION
    if event.segment == "A":
        return RecoveryStrategy.RETRY if current_hour in range(19, 22) else RecoveryStrategy.WAIT
    if event.segment == "B":
        return RecoveryStrategy.PAYMENT_METHOD_SWITCH
    if event.segment == "C":
        return RecoveryStrategy.WHATSAPP_REMINDER
    return RecoveryStrategy.RETRY


def _policy_check(event: EventRecord, strategy: RecoveryStrategy) -> bool:
    return event.transaction_amount_paise <= 5_000_000 or strategy == RecoveryStrategy.HUMAN_ESCALATION


class RazorSimulator:
    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    def run(self, events: list[EventRecord], current_hour: int = 14) -> SimulationResult:
        at_risk = sum(event.transaction_amount_paise for event in events)
        breakdown: dict[str, dict] = {}
        recovered = 0
        total_cost = 0
        discount_cost = 0
        interventions = 0
        for event in events:
            strategy = select_strategy(event, current_hour)
            name = strategy.value
            stats = breakdown.setdefault(name, {"attempts": 0, "recoveries": 0, "revenue_recovered_paise": 0, "cost_paise": 0})
            stats["attempts"] += 1
            if strategy == RecoveryStrategy.STOP or not _policy_check(event, strategy):
                continue
            interventions += 1
            cost = STRATEGY_COSTS_PAISE[name]
            stats["cost_paise"] += cost
            total_cost += cost
            in_window = current_hour in range(19, 22)
            probability = RECOVERY_PROBS.get((event.segment, name, in_window), RECOVERY_PROBS.get((event.segment, name, None), RECOVERY_PROBS[("default", None, None)]))
            if self.rng.random() < probability:
                recovered += event.transaction_amount_paise
                stats["recoveries"] += 1
                stats["revenue_recovered_paise"] += event.transaction_amount_paise
        return SimulationResult(
            total_events=len(events), total_revenue_at_risk_paise=at_risk,
            total_recovered_paise=recovered, recovery_rate=recovered / at_risk if at_risk else 0.0,
            total_interventions=interventions, total_discount_cost_paise=discount_cost,
            total_recovery_cost_paise=total_cost, net_recovered_paise=recovered - total_cost,
            strategy_breakdown=breakdown,
        )