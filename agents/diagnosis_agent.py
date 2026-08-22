"""LLM-assisted structured diagnosis with offline rule-based fallback (FR-04).

``DiagnosisAgent.diagnose(case)`` returns the FR-04 schema
``{ diagnosis, confidence, recommended_timing, reason, avoid_discount }``.

- If a Gemini client is available (API key set or a mock injected), the agent
  calls the LLM and parses/validates structured JSON.
- On any failure, or with no client, it falls back to a deterministic
  rule-based diagnosis so AC-02 holds fully offline.

Safety (NFR-05): this module is read-only. It never executes a payment and
never performs money arithmetic.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any

from config import settings

# Human-readable diagnosis per failure code.
FAILURE_DIAGNOSIS: dict[str, str] = {
    "INSUFFICIENT_FUNDS": "Insufficient balance in the customer's payment account",
    "CARD_DECLINED": "Card was declined by the issuing bank",
    "UPI_FAILURE": "UPI transaction failed (bank or network declined)",
    "NETWORK_ERROR": "Transient network error interrupted the payment",
    "AUTHENTICATION_FAILED": "Payment authentication (OTP/3DS) failed",
    "CHECKOUT_ABANDONED": "Customer abandoned checkout before completing payment",
    "FRAUD_SUSPECTED": "Payment flagged as potentially fraudulent",
}

# Low-value cases are not worth a discount.
AVOID_DISCOUNT_AMOUNT_PAISE = 100_000


@dataclass
class Diagnosis:
    diagnosis: str
    confidence: float
    recommended_timing: str
    reason: str
    avoid_discount: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _extract_json_object(text: str) -> dict | None:
    """Extract the first JSON object from possibly-noisy LLM text."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.MULTILINE).strip()
    cleaned = re.sub(r"```$", "", cleaned, flags=re.MULTILINE).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


class DiagnosisAgent:
    def __init__(self, client: Any | None = None, model: str = "gemini-pro"):
        self.model = model
        if client is not None:
            self.client = client
        elif settings.gemini_api_key:
            self.client = self._build_gemini_client()
        else:
            self.client = None

    def _build_gemini_client(self) -> Any:
        import google.generativeai as genai

        genai.configure(api_key=settings.gemini_api_key)
        return genai.GenerativeModel(self.model)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def diagnose(
        self,
        case: Any,
        customer: Any | None = None,
        profile: Any | None = None,
    ) -> Diagnosis:
        if self.client is not None:
            try:
                prompt = self._build_prompt(case, customer, profile)
                text = self._call_llm(prompt)
                parsed = self._parse_diagnosis(text)
                if parsed is not None:
                    return parsed
            except Exception:
                pass  # fall back to rule-based; never crash diagnosis
        return self._rule_based(case, profile, customer)

    # ------------------------------------------------------------------
    # LLM path
    # ------------------------------------------------------------------

    def _call_llm(self, prompt: str) -> str:
        response = self.client.generate_content(prompt)
        text = getattr(response, "text", None)
        if text is None and isinstance(response, str):
            text = response
        if not text:
            raise ValueError("empty LLM response")
        return text

    def _build_prompt(self, case: Any, customer: Any | None, profile: Any | None) -> str:
        amount = getattr(case, "amount_at_risk_paise", None)
        customer_timing = (
            f"{getattr(customer, 'typical_payment_hour_start', None)}-"
            f"{getattr(customer, 'typical_payment_hour_end', None)}"
            if customer is not None
            else "unknown"
        )
        return (
            "You are RAZOR, a payment-recovery diagnosis assistant. Given a failed payment, "
            "return ONLY a JSON object with keys: diagnosis, confidence (0-1), "
            "recommended_timing, reason, avoid_discount (bool). No markdown.\n"
            f"amount_at_risk_paise={amount}\n"
            f"failure_code={getattr(case, 'failure_code', None)}\n"
            f"failure_reason={getattr(case, 'failure_reason', None)}\n"
            f"customer_typical_hour={customer_timing}\n"
            f"overall_recovery_probability={getattr(profile, 'overall_recovery_probability', None) if profile else None}\n"
        )

    def _parse_diagnosis(self, text: str) -> Diagnosis | None:
        data = _extract_json_object(text)
        if data is None:
            return None
        required = ("diagnosis", "confidence", "recommended_timing", "reason", "avoid_discount")
        if not all(k in data for k in required):
            return None
        try:
            return Diagnosis(
                diagnosis=str(data["diagnosis"]),
                confidence=float(data["confidence"]),
                recommended_timing=str(data["recommended_timing"]),
                reason=str(data["reason"]),
                avoid_discount=bool(data["avoid_discount"]),
            )
        except (TypeError, ValueError):
            return None

    # ------------------------------------------------------------------
    # Rule-based fallback (offline, deterministic)
    # ------------------------------------------------------------------

    def _rule_based(
        self,
        case: Any,
        profile: Any | None,
        customer: Any | None,
    ) -> Diagnosis:
        failure_code = getattr(case, "failure_code", None)
        diagnosis = FAILURE_DIAGNOSIS.get(failure_code, "Payment failed for an unknown reason")

        raw_confidence = getattr(profile, "overall_recovery_probability", None)
        confidence = float(raw_confidence) if raw_confidence is not None else 0.4
        confidence = max(0.0, min(1.0, confidence))

        start = getattr(customer, "typical_payment_hour_start", None) if customer else None
        end = getattr(customer, "typical_payment_hour_end", None) if customer else None
        recommended_timing = (
            f"Between {start}:00 and {end}:00"
            if start is not None and end is not None
            else "Any time"
        )

        amount = getattr(case, "amount_at_risk_paise", None) or 0
        avoid_discount = amount < AVOID_DISCOUNT_AMOUNT_PAISE
        reason = (
            f"Rule-based diagnosis for failure '{failure_code or 'unknown'}' using "
            f"historical recovery probability {confidence:.2f}"
        )
        return Diagnosis(
            diagnosis=diagnosis,
            confidence=confidence,
            recommended_timing=recommended_timing,
            reason=reason,
            avoid_discount=avoid_discount,
        )
