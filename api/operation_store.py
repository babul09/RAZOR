"""Small in-process store for the latest successful operation results."""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any

_LOCK = threading.Lock()
_LATEST_SIMULATION: dict[str, Any] | None = None
_OPERATIONS: dict[str, dict[str, Any]] = {}


def save_simulation(result: dict[str, Any]) -> None:
    global _LATEST_SIMULATION
    with _LOCK:
        _LATEST_SIMULATION = dict(result)


def latest_simulation() -> dict[str, Any] | None:
    with _LOCK:
        return dict(_LATEST_SIMULATION) if _LATEST_SIMULATION is not None else None


def set_operation(job_id: str, **fields: Any) -> None:
    with _LOCK:
        record = _OPERATIONS.setdefault(job_id, {})
        record.update(fields)
        record["updated_at"] = datetime.now(timezone.utc)


def get_operation(job_id: str) -> dict[str, Any] | None:
    with _LOCK:
        record = _OPERATIONS.get(job_id)
        return dict(record) if record is not None else None
