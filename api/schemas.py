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


class AnalyticsOverview(BaseModel):
    revenue_at_risk_paise: int
    recovered_paise: int
    recovery_rate: float
    total_cases: int
    recovered_cases: int


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
    status: str  # PENDING | SUCCESS | FAILURE
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
