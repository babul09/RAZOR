"""Deterministic recovery state machine over RecoveryCaseStatus."""
from __future__ import annotations

from enum import Enum

from db.models import RecoveryCaseStatus


class StateEvent(str, Enum):
    """Events that drive deterministic state transitions."""
    DIAGNOSED = "DIAGNOSED"
    PREDICTED = "PREDICTED"
    STRATEGY_SELECTED = "STRATEGY_SELECTED"
    POLICY_PASSED = "POLICY_PASSED"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    APPROVED = "APPROVED"
    EXECUTED = "EXECUTED"
    VERIFY_SUCCESS = "VERIFY_SUCCESS"
    VERIFY_FAILURE = "VERIFY_FAILURE"
    NEXT_STRATEGY = "NEXT_STRATEGY"
    STOP = "STOP"


# (from_status, event) -> to_status. Follows FR-09's flow:
# NEW -> DIAGNOSING -> PREDICTED -> STRATEGY_SELECTED -> POLICY_CHECK ->
# AWAITING_APPROVAL -> EXECUTING -> VERIFYING -> [RECOVERED | FAILED ... STOPPED].
# NEXT_STRATEGY is a transition label (FAILED -> try next candidate); the
# RecoveryCaseStatus enum is left unchanged.
_TRANSITIONS: dict[tuple[RecoveryCaseStatus, StateEvent], RecoveryCaseStatus] = {
    (RecoveryCaseStatus.NEW, StateEvent.DIAGNOSED): RecoveryCaseStatus.DIAGNOSING,
    (RecoveryCaseStatus.DIAGNOSING, StateEvent.PREDICTED): RecoveryCaseStatus.PREDICTED,
    (RecoveryCaseStatus.PREDICTED, StateEvent.STRATEGY_SELECTED): RecoveryCaseStatus.STRATEGY_SELECTED,
    (RecoveryCaseStatus.STRATEGY_SELECTED, StateEvent.POLICY_PASSED): RecoveryCaseStatus.POLICY_CHECK,
    (RecoveryCaseStatus.POLICY_CHECK, StateEvent.APPROVED): RecoveryCaseStatus.EXECUTING,
    (RecoveryCaseStatus.POLICY_CHECK, StateEvent.POLICY_BLOCKED): RecoveryCaseStatus.AWAITING_APPROVAL,
    (RecoveryCaseStatus.AWAITING_APPROVAL, StateEvent.APPROVED): RecoveryCaseStatus.EXECUTING,
    (RecoveryCaseStatus.AWAITING_APPROVAL, StateEvent.STOP): RecoveryCaseStatus.STOPPED,
    (RecoveryCaseStatus.EXECUTING, StateEvent.EXECUTED): RecoveryCaseStatus.VERIFYING,
    (RecoveryCaseStatus.VERIFYING, StateEvent.VERIFY_SUCCESS): RecoveryCaseStatus.RECOVERED,
    (RecoveryCaseStatus.VERIFYING, StateEvent.VERIFY_FAILURE): RecoveryCaseStatus.FAILED,
    (RecoveryCaseStatus.FAILED, StateEvent.NEXT_STRATEGY): RecoveryCaseStatus.STRATEGY_SELECTED,
    (RecoveryCaseStatus.FAILED, StateEvent.STOP): RecoveryCaseStatus.STOPPED,
}

_TERMINAL = {
    RecoveryCaseStatus.RECOVERED,
    RecoveryCaseStatus.FAILED,
    RecoveryCaseStatus.STOPPED,
}


class RecoveryStateMachine:
    """Deterministic transitions over RecoveryCaseStatus."""

    def __init__(self, transitions: dict | None = None):
        self.transitions = transitions if transitions is not None else _TRANSITIONS

    def next_status(self, status: RecoveryCaseStatus, event: StateEvent) -> RecoveryCaseStatus:
        key = (status, event)
        if key not in self.transitions:
            raise ValueError(f"Invalid transition: {status.value} --{event.value}--> ?")
        return self.transitions[key]

    def can_transition(self, status: RecoveryCaseStatus, event: StateEvent) -> bool:
        return (status, event) in self.transitions

    def is_terminal(self, status: RecoveryCaseStatus) -> bool:
        return status in _TERMINAL

    @property
    def transitions(self) -> dict:
        return self._transitions

    @transitions.setter
    def transitions(self, value: dict) -> None:
        self._transitions = value
