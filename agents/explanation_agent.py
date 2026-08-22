"""Human-readable explanation agent for the dashboard (Phase 4).

Generates a short explanation from a ``Decision`` + diagnosis. Uses a gated
Gemini-flash path when a client is available; otherwise a deterministic
template. Read-only: never executes a payment, never writes to the DB.
"""
from __future__ import annotations

from typing import Any

from config import settings


class ExplanationAgent:
    def __init__(self, client: Any | None = None, model: str = "gemini-2.5-flash"):
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

    def explain(self, decision: Any, diagnosis: Any) -> str:
        if self.client is not None:
            try:
                prompt = (
                    "In one short sentence, explain this RAZOR recovery decision for a "
                    "non-technical dashboard user. "
                    f"strategy={getattr(decision, 'selected_strategy', None)} "
                    f"reason={getattr(decision, 'reasoning', '')} "
                    f"diagnosis={getattr(diagnosis, 'diagnosis', '')}. "
                    "Plain language, no markdown."
                )
                response = self.client.generate_content(prompt)
                text = getattr(response, "text", None)
                if text:
                    return text.strip()
            except Exception:
                pass  # fall back to template
        return self._template(decision, diagnosis)

    def _template(self, decision: Any, diagnosis: Any) -> str:
        strategy = getattr(decision, "selected_strategy", "no strategy")
        reason = getattr(decision, "reasoning", "no reason given")
        diagnosis_text = getattr(diagnosis, "diagnosis", "no diagnosis")
        return (
            f"Selected {strategy} because {reason}. "
            f"Diagnosis: {diagnosis_text}."
        )
