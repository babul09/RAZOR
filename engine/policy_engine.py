"""Policy / guardrail engine (FR-07) — a hard gate before every action.

Loads a merchant policy from YAML (or a ``MerchantPolicy``) and enforces all 7
guardrail checks. A non-PASS result routes the action to human review or blocks
it outright, and is always audited.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

CHANNEL_BY_STRATEGY = {
    "WHATSAPP_REMINDER": "whatsapp",
    "EMAIL_REMINDER": "email",
}


@dataclass
class MerchantPolicy:
    """7 guardrail fields plus a configurable per-merchant WAIT window."""

    merchant_id: str
    max_discount_percent: int = 10
    max_automated_amount_paise: int = 500_000
    max_contacts_count: int = 3
    max_contacts_window_days: int = 7
    require_human_approval_above_paise: int = 500_000
    allowed_channels: list[str] = field(default_factory=lambda: ["whatsapp", "email"])
    stop_if_payment_succeeds: bool = True
    wait_window_start_hour: int | None = 19
    wait_window_end_hour: int | None = 22

    @property
    def wait_window(self) -> tuple[int | None, int | None]:
        return (self.wait_window_start_hour, self.wait_window_end_hour)

    @property
    def max_discount_rate(self) -> float:
        return self.max_discount_percent / 100.0


def load_policy_yaml(path: str | Path) -> MerchantPolicy:
    """Load a ``MerchantPolicy`` from YAML, applying defaults for missing fields."""
    path = Path(path)
    if not path.exists():
        raise ValueError(f"Policy file not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Malformed policy YAML: {exc}") from exc
    if not isinstance(data, dict) or "merchant_id" not in data:
        raise ValueError(f"Policy file must contain a 'merchant_id': {path}")

    wait = data.get("wait") or {}
    allowed = data.get("allowed_channels")
    if allowed is not None and not isinstance(allowed, list):
        raise ValueError("allowed_channels must be a list")
    if not isinstance(allowed, list):
        allowed = ["whatsapp", "email"]

    policy = MerchantPolicy(
        merchant_id=str(data["merchant_id"]),
        max_discount_percent=int(data.get("max_discount_percent", 10)),
        max_automated_amount_paise=int(data.get("max_automated_amount_paise", 500_000)),
        max_contacts_count=int(data.get("max_contacts_count", 3)),
        max_contacts_window_days=int(data.get("max_contacts_window_days", 7)),
        require_human_approval_above_paise=int(
            data.get("require_human_approval_above_paise", 500_000)
        ),
        allowed_channels=allowed,
        stop_if_payment_succeeds=bool(data.get("stop_if_payment_succeeds", True)),
        wait_window_start_hour=int(wait["window_start_hour"]) if wait.get("window_start_hour") is not None else 19,
        wait_window_end_hour=int(wait["window_end_hour"]) if wait.get("window_end_hour") is not None else 22,
    )
    return policy


@dataclass
class PolicyResult:
    status: str  # PASS | APPROVAL_REQUIRED | BLOCK
    reason: str | None = None

    @property
    def passed(self) -> bool:
        return self.status == "PASS"


class PolicyEngine:
    """Enforces the 7 guardrail checks as a hard gate before any action."""

    def __init__(self, policy: MerchantPolicy):
        self.policy = policy

    def check(
        self,
        decision: Any,
        amount_paise: int,
        discount_rate: float = 0.0,
        contacts_in_window: int = 0,
        payment_succeeded: bool = False,
    ) -> PolicyResult:
        """Return PASS / APPROVAL_REQUIRED / BLOCK for the selected strategy."""
        strategy = getattr(decision, "selected_strategy", None)
        # WAIT/STOP take no immediate action -> nothing to gate.
        if strategy in ("WAIT", "STOP"):
            return PolicyResult("PASS")

        p = self.policy

        # 1. max_discount_percent
        if strategy == "DISCOUNT_OFFER" and discount_rate > p.max_discount_rate:
            return PolicyResult(
                "BLOCK",
                f"discount_rate {discount_rate:.0%} exceeds max_discount_percent {p.max_discount_percent}%",
            )

        # 2. max_automated_amount_paise
        if amount_paise > p.max_automated_amount_paise:
            return PolicyResult(
                "APPROVAL_REQUIRED",
                f"amount {amount_paise} exceeds max_automated_amount_paise {p.max_automated_amount_paise}",
            )

        # 3. max_contacts_count
        if contacts_in_window >= p.max_contacts_count:
            return PolicyResult(
                "BLOCK",
                f"contacts in window {contacts_in_window} >= max_contacts_count {p.max_contacts_count}",
            )

        # 4. max_contacts_window_days is represented by the windowed contact count
        #    (caller passes contacts_in_window computed over the window).

        # 5. require_human_approval_above_paise
        if amount_paise > p.require_human_approval_above_paise:
            return PolicyResult(
                "APPROVAL_REQUIRED",
                f"amount {amount_paise} exceeds require_human_approval_above_paise {p.require_human_approval_above_paise}",
            )

        # 6. allowed_channels
        channel = CHANNEL_BY_STRATEGY.get(strategy)
        if channel is not None and channel not in p.allowed_channels:
            return PolicyResult(
                "BLOCK",
                f"channel '{channel}' not in allowed_channels {p.allowed_channels}",
            )

        # 7. stop_if_payment_succeeds
        if p.stop_if_payment_succeeds and payment_succeeded:
            return PolicyResult("BLOCK", "payment already succeeded; stop_if_payment_succeeds")

        return PolicyResult("PASS")
