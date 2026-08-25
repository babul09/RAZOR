"""Simulation endpoints (FR-13): dispatch + status polling.

For a demo, the simulation runs on a background thread so the status endpoint
can report honest stage progress (generating -> baseline -> razor -> complete)
and the dashboard can show a live loading bar. Operation state is kept in the
in-process ``operation_store``; ``execution_mode`` makes clear this is the
inline demo path, not a Celery/Redis worker. Results are returned via the status
endpoint keyed by the job id.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import asdict

from fastapi import APIRouter

from api.errors import http_error
from api.operation_store import get_operation, set_operation
from api.schemas import (
    SimulationRunRequest,
    SimulationRunResponse,
    SimulationStatusResponse,
)
from simulation.baseline_simulator import BaselineSimulator
from simulation.generator import SyntheticDataGenerator
from simulation.razor_simulator import RazorSimulator

router = APIRouter(prefix="/api/simulation", tags=["simulation"])

STAGES = ("generating", "baseline", "razor", "complete")
TOTAL_STAGES = len(STAGES)


def _run_inline(job_id: str, n_events: int, seed: int, hour: int) -> None:
    """Run the comparison on a worker thread, publishing stage progress."""
    try:
        set_operation(
            job_id,
            status="running",
            stage=STAGES[0],
            completed=1,
            total=TOTAL_STAGES,
            execution_mode="inline-process",
        )
        dataset = SyntheticDataGenerator(seed=seed).generate(n_events)
        set_operation(job_id, status="running", stage=STAGES[1], completed=2, total=TOTAL_STAGES)
        baseline = BaselineSimulator(seed=seed).run(dataset.events)
        set_operation(job_id, status="running", stage=STAGES[2], completed=3, total=TOTAL_STAGES)
        razor = RazorSimulator(seed=seed).run(dataset.events, current_hour=hour)
        result = {
            "baseline": asdict(baseline),
            "razor": asdict(razor),
            "incremental_paise": razor.net_recovered_paise - baseline.net_recovered_paise,
        }
        set_operation(
            job_id,
            status="succeeded",
            stage=STAGES[3],
            completed=TOTAL_STAGES,
            total=TOTAL_STAGES,
            execution_mode="inline-process",
            result=result,
        )
    except Exception as exc:  # noqa: BLE001 - surface a sanitized failure to the UI
        set_operation(
            job_id,
            status="failed",
            stage=None,
            completed=0,
            total=TOTAL_STAGES,
            execution_mode="inline-process",
            error=str(exc),
        )


@router.post("/run", response_model=SimulationRunResponse)
def run_simulation(body: SimulationRunRequest) -> SimulationRunResponse:
    if body.n_events < 1:
        raise http_error(400, "invalid_n_events", "n_events must be positive")

    job_id = f"sync_{uuid.uuid4().hex}"
    set_operation(
        job_id,
        status="queued",
        stage="queued",
        completed=0,
        total=TOTAL_STAGES,
        execution_mode="inline-process",
    )
    thread = threading.Thread(
        target=_run_inline,
        args=(job_id, body.n_events, body.seed, body.hour),
        daemon=True,
    )
    thread.start()
    return SimulationRunResponse(job_id=job_id)


@router.get("/status/{job_id}", response_model=SimulationStatusResponse)
def simulation_status(job_id: str) -> SimulationStatusResponse:
    record = get_operation(job_id)
    if record is None:
        return SimulationStatusResponse(
            status="failed",
            stage=None,
            completed=0,
            total=TOTAL_STAGES,
            execution_mode="inline-process",
            error="unknown job",
        )
    return SimulationStatusResponse(**record)
