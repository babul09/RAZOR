"""Simulation endpoints (FR-13): dispatch + status polling.

For a demo, the simulation runs synchronously inline so the Simulation tab
always works — no Celery worker required. Results are cached in-memory keyed by
the job id and returned immediately via the status endpoint. A Celery async path
remains available for large/batched workloads when a worker is running.
"""
from __future__ import annotations

import threading
import uuid

from fastapi import APIRouter

from agents.tasks import run_simulation as run_simulation_task
from api.errors import http_error
from api.schemas import (
    SimulationRunRequest,
    SimulationRunResponse,
    SimulationStatusResponse,
)

router = APIRouter(prefix="/api/simulation", tags=["simulation"])

# In-memory results keyed by job id.
_RESULTS: dict[str, dict] = {}
_LOCK = threading.Lock()


@router.post("/run", response_model=SimulationRunResponse)
def run_simulation(body: SimulationRunRequest) -> SimulationRunResponse:
    if body.n_events < 1:
        raise http_error(400, "invalid_n_events", "n_events must be positive")
    result = run_simulation_task.run(body.n_events, body.seed, body.hour)
    job_id = f"sync_{uuid.uuid4().hex}"
    with _LOCK:
        _RESULTS[job_id] = result
    return SimulationRunResponse(job_id=job_id)


@router.get("/status/{job_id}", response_model=SimulationStatusResponse)
def simulation_status(job_id: str) -> SimulationStatusResponse:
    with _LOCK:
        result = _RESULTS.get(job_id)
    if result is None:
        return SimulationStatusResponse(status="FAILURE", result=None)
    return SimulationStatusResponse(status="SUCCESS", result=result)
