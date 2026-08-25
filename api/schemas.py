"""Pydantic response schemas for the RAZOR API (integer-paise money, NFR-03)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class CaseSummary(BaseModel):
    id: str
    customer_id: str
    amount_at_risk_paise: int
    failure_code: str | None = None
    status: str
    priority: int = 0
    recovery_probability: float | None = None
    created_at: datetime | None = None


class TimelineEntry(BaseModel):
    type: str
    event_type: str
    detail: dict[str, Any] | None = None
    created_at: datetime | None = None


class CaseDetail(CaseSummary):
    source_type: str | None = None
    source_id: str | None = None
    failure_reason: str | None = None
    timeline: list[TimelineEntry] = []


class PaginatedCases(BaseModel):
    items: list[CaseSummary]
    total: int
    page: int
    page_size: int


class OverviewSourceMetric(BaseModel):
    source_type: str
    at_risk_paise: int = 0
    recovered_paise: int = 0


class AnalyticsOverview(BaseModel):
    revenue_at_risk_paise: int
    recovered_paise: int
    recovery_rate: float
    total_cases: int
    recovered_cases: int
    # At-risk value over cases that actually reached an executed outcome (the
    # measured-real-batch scope used for the baseline / incremental headline).
    executed_at_risk_paise: int = 0
    # Measured money: incremental vs a baseline over the EXECUTED batch. None
    # when no recovery outcome has been executed yet (honest no-data state).
    incremental_paise: int | None = None
    # Per revenue-risk source type breakdown (executed outcomes).
    by_source: list[OverviewSourceMetric] = []


class BatchSourceMetric(BaseModel):
    source_type: str
    processed: int = 0
    attempts: int = 0
    recoveries: int = 0
    at_risk_paise: int = 0
    recovered_paise: int = 0
    cost_paise: int = 0


class RecoveryBatchRequest(BaseModel):
    source_types: list[str] | None = None
    limit: int = 100


class RecoveryBatchReport(BaseModel):
    processed_cases: int
    executed: int
    recoveries: int
    at_risk_paise: int
    recovered_paise: int
    cost_paise: int
    incremental_paise: int
    per_source: list[BatchSourceMetric]


class StrategyMetric(BaseModel):
    strategy: str
    attempts: int
    recoveries: int
    recovered_paise: int
    cost_paise: int


class SimulationRunRequest(BaseModel):
    n_events: int = 10_000
    seed: int = 42
    hour: int = 14


class SimulationRunResponse(BaseModel):
    job_id: str


class SimulationStatusResponse(BaseModel):
    status: str  # queued | running | succeeded | failed
    stage: str | None = None
    completed: int | None = None
    total: int | None = None
    execution_mode: str | None = None
    error: str | None = None
    result: dict[str, Any] | None = None


class ExperimentArmMetric(BaseModel):
    experiment_id: str
    experiment_name: str
    arm_name: str
    traffic_percent: float
    strategy: str | None = None
    attempts: int = 0
    recoveries: int = 0
    revenue_recovered_paise: int = 0
    recovery_rate: float | None = None


class ExperimentArmCreate(BaseModel):
    arm_name: str
    traffic_percent: int
    strategy: str | None = None


class ExperimentCreateRequest(BaseModel):
    name: str
    merchant_id: str
    arms: list[ExperimentArmCreate]


class ExperimentCreateResponse(BaseModel):
    id: str
    name: str
    status: str
    arms: list[ExperimentArmMetric]


class EventIngestRequest(BaseModel):
    event_id: str
    event_type: str
    merchant_id: str
    customer_id: str
    amount_paise: int
    payment_method: str | None = None
    failure_code: str | None = None
    timestamp: str | None = None


class EventIngestResponse(BaseModel):
    event_id: str
    event_type: str
    ingested: bool
    duplicate: bool = False
    recovery_case_id: str | None = None


# --- Razorpay integration (Phase 9) ---


class RazorpayHealth(BaseModel):
    configured: bool
    mode: str  # "test" | "demo"
    key_id_masked: str | None = None


class RazorpayPayment(BaseModel):
    id: str
    amount_paise: int
    currency: str = "INR"
    status: str
    method: str
    email: str | None = None
    contact: str | None = None
    failure_code: str | None = None
    failure_reason: str | None = None
    created_at: int | None = None


class RazorpayLink(BaseModel):
    id: str
    amount_paise: int
    status: str
    short_url: str | None = None
    created_at: int | None = None


class RazorpayRecoverRequest(BaseModel):
    payment_id: str
    name: str | None = None
    email: str | None = None
    contact: str | None = None


class RazorpayRecoverResponse(BaseModel):
    payment_id: str
    amount_paise: int
    strategy: str
    recovery_probability: float
    link_id: str | None = None
    short_url: str | None = None
    link_status: str | None = None


class RazorpaySimSide(BaseModel):
    total_recovered_paise: int
    recovery_rate: float
    net_recovered_paise: int
    interventions: int = 0


class RazorpayComparison(BaseModel):
    configured: bool
    source: str = "live"  # "live" | "sample"
    at_risk_paise: int
    baseline: RazorpaySimSide
    razor: RazorpaySimSide
    incremental_paise: int

