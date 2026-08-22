"""RAZOR FastAPI application (Phase 5)."""
from __future__ import annotations

from fastapi import FastAPI

from api.routers import analytics, events, experiments, health, recovery, simulation

app = FastAPI(title="RAZOR API", version="0.1.0")

app.include_router(health.router)
app.include_router(recovery.router)
app.include_router(analytics.router)
app.include_router(events.router)
app.include_router(simulation.router)
app.include_router(experiments.router)
