"""Celery async simulation endpoints (FR-13): dispatch + status polling."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from agents.celery_app import celery_app
from agents.tasks import run_simulation as run_simulation_task
from api.schemas import (
    SimulationRunRequest,
    SimulationRunResponse,
    SimulationStatusResponse,
)

router = APIRouter(prefix="/api/simulation", tags=["simulation"])


@router.post("/run", response_model=SimulationRunResponse)
def run_simulation(body: SimulationRunRequest) -> SimulationRunResponse:
    if body.n_events < 1:
        raise HTTPException(status_code=400, detail="n_events must be positive")
    async_result = run_simulation_task.delay(body.n_events, body.seed, body.hour)
    return SimulationRunResponse(job_id=async_result.id)


@router.get("/status/{job_id}", response_model=SimulationStatusResponse)
def simulation_status(job_id: str) -> SimulationStatusResponse:
    result = celery_app.AsyncResult(job_id)
    if result.state == "SUCCESS":
        return SimulationStatusResponse(status="SUCCESS", result=result.result)
    if result.state == "FAILURE":
        return SimulationStatusResponse(status="FAILURE", result=None)
    return SimulationStatusResponse(status=result.state, result=None)
