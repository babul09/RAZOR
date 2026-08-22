"""Public recovery-prediction API for RAZOR.

``RecoveryModel`` wraps a fitted preprocessing + estimator ``Pipeline`` and
exposes :meth:`RecoveryModel.predict_proba` — the stable contract consumed by
Phase 3's strategy engine. It normalizes strategy aliases, builds exactly one
prediction row without mutating the caller's mapping, and returns a finite
probability in ``[0, 1]``.
"""
from __future__ import annotations

import joblib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from ml.training import (
    FEATURE_COLUMNS,
    STRATEGY_ALIASES,
    TRAINING_STRATEGIES,
    normalize_strategy,
    train_logistic_regression,
)

# Version of the trusted local artifact envelope.
ARTIFACT_VERSION = 1


class RecoveryModel:
    """A fitted recovery-prediction model with a stable per-strategy API."""

    def __init__(self, pipeline: Any, feature_columns: list[str] | None = None):
        self.pipeline = pipeline
        self.feature_columns = list(feature_columns or FEATURE_COLUMNS)

    @classmethod
    def train(cls, events: list[Any], seed: int = 42) -> "RecoveryModel":
        """Train a logistic-regression baseline from deterministic events."""
        pipeline = train_logistic_regression(events, seed)
        return cls(pipeline)

    def predict_proba(self, features: Mapping[str, Any], strategy: str) -> float:
        """Return ``P(recovery | features, strategy)`` as a float in ``[0, 1]``.

        ``features`` must supply the event-level feature values (all columns in
        ``feature_columns`` except ``candidate_strategy``). The caller's mapping
        is never mutated. ``strategy`` may be a canonical name or a roadmap alias.
        """
        normalized = normalize_strategy(strategy)
        row = {
            col: features[col]
            for col in self.feature_columns
            if col != "candidate_strategy"
        }
        row["candidate_strategy"] = normalized
        frame = pd.DataFrame([row])[self.feature_columns]
        probability = self.pipeline.predict_proba(frame)[0][1]
        return float(probability)

    # ------------------------------------------------------------------
    # Persistence (Plan 02) — trusted local artifacts only
    # ------------------------------------------------------------------

    def save(self, path: str | Path, metrics: dict | None = None) -> None:
        """Persist this model as a versioned joblib envelope to ``path``.

        Creates parent directories as needed. The envelope carries the fitted
        preprocessing + estimator, feature columns, strategy metadata, metrics,
        and training metadata so reload is self-describing.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        envelope = {
            "version": ARTIFACT_VERSION,
            "model": self.pipeline,
            "feature_columns": list(self.feature_columns),
            "strategy_aliases": dict(STRATEGY_ALIASES),
            "canonical_strategies": list(TRAINING_STRATEGIES),
            "metrics": metrics,
            "trained_at": datetime.now(timezone.utc).isoformat(),
        }
        joblib.dump(envelope, path)

    @classmethod
    def load(cls, path: str | Path) -> "RecoveryModel":
        """Load a trusted artifact produced by :meth:`save`.

        Validates the versioned envelope, required keys, and exact
        feature-column equality. Raises ``ValueError`` for malformed or
        mismatched artifacts.
        """
        path = Path(path)
        envelope = joblib.load(path)

        if not isinstance(envelope, dict) or "model" not in envelope:
            raise ValueError(f"Malformed model artifact: {path}")
        if envelope.get("version") != ARTIFACT_VERSION:
            raise ValueError(
                f"Unsupported artifact version: {envelope.get('version')!r} "
                f"(expected {ARTIFACT_VERSION})"
            )
        required_keys = (
            "model",
            "feature_columns",
            "strategy_aliases",
            "canonical_strategies",
        )
        missing = [key for key in required_keys if key not in envelope]
        if missing:
            raise ValueError(f"Artifact missing required keys: {missing}")

        feature_columns = list(envelope["feature_columns"])
        if feature_columns != FEATURE_COLUMNS:
            raise ValueError(
                f"Feature-column mismatch: artifact has {feature_columns!r}, "
                f"expected {FEATURE_COLUMNS!r}"
            )
        return cls(envelope["model"], feature_columns=feature_columns)
