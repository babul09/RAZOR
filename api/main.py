"""RAZOR FastAPI application (Phase 5)."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.errors import register_exception_handlers
from api.routers import analytics, events, experiments, health, razorpay, recovery, simulation

app = FastAPI(title="RAZOR API", version="0.1.0")

# Demo dashboard is served from a different origin (Next.js); allow all.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(health.router)
app.include_router(recovery.router)
app.include_router(analytics.router)
app.include_router(events.router)
app.include_router(simulation.router)
app.include_router(experiments.router)
app.include_router(razorpay.router)
