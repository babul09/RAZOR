"""Regression tests for public operation status and provenance contracts."""
from __future__ import annotations

from api.operation_store import get_operation, set_operation
from api.schemas import AnalyticsOverview, SimulationStatusResponse


def test_operation_status_has_safe_lifecycle_fields():
    set_operation(
        "contract-test",
        status="succeeded",
        stage="complete",
        completed=10,
        total=10,
        execution_mode="inline-process",
        result={"incremental_paise": 123},
    )
    status = SimulationStatusResponse(**get_operation("contract-test"))
    assert status.status == "succeeded"
    assert status.stage == "complete"
    assert status.execution_mode == "inline-process"
    assert status.result["incremental_paise"] == 123
    assert status.error is None


def test_failed_operation_exposes_sanitized_error_only():
    set_operation(
        "failed-contract-test",
        status="failed",
        stage="diagnosis",
        execution_mode="inline-process",
        error="operation failed",
    )
    status = SimulationStatusResponse(**get_operation("failed-contract-test"))
    assert status.status == "failed"
    assert status.error == "operation failed"
    assert "api_key" not in status.error.lower()
    assert "prompt" not in status.error.lower()


def test_overview_comparison_is_optional_integer_paise():
    empty = AnalyticsOverview(
        revenue_at_risk_paise=0,
        recovered_paise=0,
        recovery_rate=0,
        total_cases=0,
        recovered_cases=0,
    )
    populated = empty.model_copy(update={"incremental_paise": -250})
    assert empty.incremental_paise is None
    assert isinstance(populated.incremental_paise, int)