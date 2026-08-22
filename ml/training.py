"""Deterministic, offline feature construction and training for RAZOR recovery prediction.

This module owns the canonical Phase 2 feature contract (``FEATURE_COLUMNS``),
the counterfactual training-frame builder (one row per event x candidate
strategy), and the scikit-learn logistic-regression baseline pipeline.

Design constraints:
- Amounts / LTV stay as integer paise inputs; only ML preprocessing produces floats.
- The hidden synthetic ``segment``/``segment_encoded`` is excluded from model features
  (used only to derive deterministic synthetic labels).
- Everything is fully offline and deterministic given a seed.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from simulation.generator import EventRecord
from simulation.razor_simulator import RECOVERY_PROBS

# Canonical Phase 2 candidate strategies (subset of the RecoveryStrategy enum).
TRAINING_STRATEGIES: tuple[str, ...] = (
    "RETRY",
    "PAYMENT_METHOD_SWITCH",
    "WHATSAPP_REMINDER",
    "EMAIL_REMINDER",
    "DISCOUNT_OFFER",
)

# Roadmap shorthand aliases -> canonical enum values.
STRATEGY_ALIASES: dict[str, str] = {
    "METHOD_SWITCH": "PAYMENT_METHOD_SWITCH",
    "WHATSAPP": "WHATSAPP_REMINDER",
    "EMAIL": "EMAIL_REMINDER",
    "DISCOUNT": "DISCOUNT_OFFER",
}

# Exactly 12 declared model features (FR-05). No segment leakage.
FEATURE_COLUMNS: list[str] = [
    "transaction_amount_paise",
    "payment_method",
    "failure_code",
    "customer_ltv_paise",
    "previous_successes",
    "previous_failures",
    "time_since_last_payment_days",
    "historical_payment_hour",
    "historical_payment_day",
    "previous_strategy",
    "previous_strategy_success_rate",
    "candidate_strategy",
]

CATEGORICAL_FEATURES: list[str] = [
    "payment_method",
    "failure_code",
    "previous_strategy",
    "candidate_strategy",
]

NUMERIC_FEATURES: list[str] = [
    "transaction_amount_paise",
    "customer_ltv_paise",
    "previous_successes",
    "previous_failures",
    "time_since_last_payment_days",
    "historical_payment_hour",
    "historical_payment_day",
    "previous_strategy_success_rate",
]

# Deterministic "previously attempted" strategy per synthetic segment, mirroring
# the Phase 1 simulator's natural selection bias. Only used to derive the
# observable ``previous_strategy``/``previous_strategy_success_rate`` features,
# never exposed as model features themselves.
_SEGMENT_NATURAL_STRATEGY: dict[str, str] = {
    "A": "RETRY",
    "B": "PAYMENT_METHOD_SWITCH",
    "C": "WHATSAPP_REMINDER",
    "D": "RETRY",
    "E": "RETRY",
}

# Maps a canonical strategy to the EventRecord attribute holding that channel's
# observed success rate, used as the prior ``previous_strategy_success_rate``.
_STRATEGY_RATE_ATTR: dict[str, str] = {
    "RETRY": "retry_success_rate",
    "PAYMENT_METHOD_SWITCH": "upi_switch_success_rate",
    "WHATSAPP_REMINDER": "whatsapp_success_rate",
    "EMAIL_REMINDER": "email_success_rate",
    "DISCOUNT_OFFER": "retry_success_rate",
}


def normalize_strategy(strategy: str) -> str:
    """Normalize a strategy name/alias to a canonical Phase 2 value.

    Case-insensitive and whitespace-trimmed. Unsupported values raise
    ``ValueError`` before any model inference.
    """
    if not isinstance(strategy, str):
        raise ValueError(f"strategy must be a string, got {type(strategy).__name__}")
    value = strategy.strip().upper()
    canonical = STRATEGY_ALIASES.get(value, value)
    if canonical not in TRAINING_STRATEGIES:
        raise ValueError(f"Unsupported recovery strategy: {strategy!r}")
    return canonical


def _previous_strategy(event: EventRecord) -> str:
    return _SEGMENT_NATURAL_STRATEGY.get(event.segment, "RETRY")


def _previous_strategy_success_rate(event: EventRecord, strategy: str) -> float:
    return float(getattr(event, _STRATEGY_RATE_ATTR[strategy]))


def _oracle_probability(event: EventRecord, strategy: str) -> float:
    """Look up the simulator oracle probability for (segment, strategy)."""
    in_window = event.historical_payment_hour in range(19, 22)
    return RECOVERY_PROBS.get(
        (event.segment, strategy, in_window),
        RECOVERY_PROBS.get(
            (event.segment, strategy, None),
            RECOVERY_PROBS[("default", None, None)],
        ),
    )


def build_training_frame(events: list[EventRecord], seed: int = 42) -> pd.DataFrame:
    """Expand every event across all candidate strategies into one labeled row each.

    Each event produces ``len(TRAINING_STRATEGIES)`` rows. ``recovered`` is a
    deterministic binary label drawn from the simulator oracle with a local
    seeded RNG. The hidden segment is never a model feature.
    """
    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    for event in events:
        prev_strategy = _previous_strategy(event)
        prev_rate = _previous_strategy_success_rate(event, prev_strategy)
        for strategy in TRAINING_STRATEGIES:
            row = {
                "transaction_amount_paise": event.transaction_amount_paise,
                "payment_method": event.payment_method,
                "failure_code": event.failure_code,
                "customer_ltv_paise": event.customer_ltv_paise,
                "previous_successes": event.previous_successes,
                "previous_failures": event.previous_failures,
                "time_since_last_payment_days": event.days_since_last_payment,
                "historical_payment_hour": event.historical_payment_hour,
                "historical_payment_day": event.historical_payment_day,
                "previous_strategy": prev_strategy,
                "previous_strategy_success_rate": prev_rate,
                "candidate_strategy": strategy,
                "recovered": int(rng.random() < _oracle_probability(event, strategy)),
            }
            rows.append(row)
    return pd.DataFrame(rows)


def build_preprocessor() -> ColumnTransformer:
    """Build the deterministic feature preprocessor (scaled numeric + one-hot categorical)."""
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
        ]
    )


def train_logistic_regression(events: list[EventRecord], seed: int = 42) -> Pipeline:
    """Train and return a fitted logistic-regression ``Pipeline`` on the frame."""
    frame = build_training_frame(events, seed)
    pipeline = Pipeline(
        steps=[
            ("preprocess", build_preprocessor()),
            ("model", LogisticRegression(max_iter=1000, random_state=seed)),
        ]
    )
    pipeline.fit(frame[FEATURE_COLUMNS], frame["recovered"])
    return pipeline


def train_xgboost(events: list[EventRecord], seed: int = 42) -> Pipeline:
    """Train and return a fitted XGBoost ``Pipeline`` on the full frame.

    Uses the same leakage-free 12-feature frame and deterministic settings as
    the logistic baseline so their metrics are comparable.
    """
    frame = build_training_frame(events, seed)
    pipeline = Pipeline(
        steps=[
            ("preprocess", build_preprocessor()),
            (
                "model",
                XGBClassifier(
                    n_estimators=100,
                    max_depth=4,
                    learning_rate=0.1,
                    random_state=seed,
                    n_jobs=1,
                    eval_metric="logloss",
                ),
            ),
        ]
    )
    pipeline.fit(frame[FEATURE_COLUMNS], frame["recovered"])
    return pipeline


def _safe_split(X: pd.DataFrame, y: pd.Series, seed: int):
    """Stratified split when both classes are sufficiently represented, else plain split."""
    classes, counts = np.unique(y, return_counts=True)
    if len(classes) >= 2 and int(counts.min()) >= 2:
        return train_test_split(X, y, test_size=0.2, random_state=seed, stratify=y)
    return train_test_split(X, y, test_size=0.2, random_state=seed)


def compare_models(events: list[EventRecord], seed: int = 42) -> dict:
    """Train logistic and XGBoost on the same holdout and return metrics + selection.

    Returns a dict with ``logistic`` and ``xgboost`` metric records (ROC-AUC,
    log_loss, Brier score) evaluated on one deterministic holdout, plus
    ``selected_model`` (name) and ``pipeline`` (the selected fitted estimator).

    Selection rule (deterministic): prefer higher ROC-AUC; tie-break on lower
    log_loss. There is no hard-coded winner.
    """
    frame = build_training_frame(events, seed)
    X = frame[FEATURE_COLUMNS]
    y = frame["recovered"]
    X_train, X_test, y_train, y_test = _safe_split(X, y, seed)

    candidates = {
        "logistic": Pipeline(
            steps=[
                ("preprocess", build_preprocessor()),
                ("model", LogisticRegression(max_iter=1000, random_state=seed)),
            ]
        ),
        "xgboost": Pipeline(
            steps=[
                ("preprocess", build_preprocessor()),
                (
                    "model",
                    XGBClassifier(
                        n_estimators=100,
                        max_depth=4,
                        learning_rate=0.1,
                        random_state=seed,
                        n_jobs=1,
                        eval_metric="logloss",
                    ),
                ),
            ]
        ),
    }

    metrics: dict[str, dict[str, float]] = {}
    for name, pipeline in candidates.items():
        pipeline.fit(X_train, y_train)
        proba = pipeline.predict_proba(X_test)[:, 1]
        metrics[name] = {
            "roc_auc": float(roc_auc_score(y_test, proba)),
            "log_loss": float(log_loss(y_test, proba)),
            "brier": float(brier_score_loss(y_test, proba)),
        }

    # Deterministic selection: higher ROC-AUC wins; tie-break on lower log_loss.
    log_auc, xgb_auc = metrics["logistic"]["roc_auc"], metrics["xgboost"]["roc_auc"]
    if log_auc > xgb_auc:
        selected = "logistic"
    elif xgb_auc > log_auc:
        selected = "xgboost"
    else:
        selected = (
            "logistic"
            if metrics["logistic"]["log_loss"] <= metrics["xgboost"]["log_loss"]
            else "xgboost"
        )

    return {
        "logistic": metrics["logistic"],
        "xgboost": metrics["xgboost"],
        "selected_model": selected,
        "pipeline": candidates[selected],
    }
