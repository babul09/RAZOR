"""Offline unit tests for the Phase 2 recovery-prediction ML layer."""
from __future__ import annotations

import math
import subprocess
import sys

import joblib
import pytest

from ml.recovery_model import RecoveryModel
from ml.training import (
    FEATURE_COLUMNS,
    TRAINING_STRATEGIES,
    build_training_frame,
    compare_models,
    normalize_strategy,
    train_logistic_regression,
    train_xgboost,
)
from simulation.generator import SyntheticDataGenerator


@pytest.fixture(scope="module")
def events():
    return SyntheticDataGenerator(seed=42).generate(20).events


def _features_from_row(row):
    return {k: row[k] for k in FEATURE_COLUMNS if k != "candidate_strategy"}


# ---------------------------------------------------------------------------
# Plan 01 — contract, frame, prediction API
# ---------------------------------------------------------------------------


def test_contract_constants():
    assert len(FEATURE_COLUMNS) == 12
    assert len(TRAINING_STRATEGIES) == 5
    assert normalize_strategy("retry") == "RETRY"
    assert normalize_strategy(" method_switch ") == "PAYMENT_METHOD_SWITCH"
    assert normalize_strategy("whatsapp") == "WHATSAPP_REMINDER"
    assert normalize_strategy("email") == "EMAIL_REMINDER"
    assert normalize_strategy("discount") == "DISCOUNT_OFFER"


def test_training_frame_has_required_features(events):
    frame = build_training_frame(events, seed=42)
    assert len(frame) == 20 * len(TRAINING_STRATEGIES)  # 100 rows
    assert "recovered" in frame.columns
    assert set(FEATURE_COLUMNS).issubset(frame.columns)
    # No hidden segment leakage.
    assert "segment" not in frame.columns
    assert "segment_encoded" not in frame.columns
    assert frame["recovered"].isin([0, 1]).all()


def test_predict_proba_all_phase2_strategies(events):
    model = RecoveryModel.train(events, seed=42)
    row = build_training_frame(events, seed=42).iloc[0]
    features = _features_from_row(row)
    for strategy in ["RETRY", "METHOD_SWITCH", "WHATSAPP", "EMAIL", "DISCOUNT"]:
        prob = model.predict_proba(features, strategy)
        assert 0.0 <= prob <= 1.0
        assert math.isfinite(prob)


def test_invalid_strategy_is_rejected(events):
    model = RecoveryModel.train(events, seed=42)
    row = build_training_frame(events, seed=42).iloc[0]
    features = _features_from_row(row)
    with pytest.raises(ValueError):
        model.predict_proba(features, "PAYMENT_LINK")
    with pytest.raises(ValueError):
        model.predict_proba(features, "not-a-strategy")


def test_money_features_remain_paise_inputs(events):
    model = RecoveryModel.train(events, seed=42)
    row = build_training_frame(events, seed=42).iloc[0]
    features = _features_from_row(row)
    features["transaction_amount_paise"] = 123456789
    features["customer_ltv_paise"] = 987654321
    before = dict(features)
    prob = model.predict_proba(features, "RETRY")
    assert 0.0 <= prob <= 1.0
    # Caller's mapping is not mutated.
    assert features == before


def test_training_smoke_offline(events):
    pipeline = train_logistic_regression(events, seed=42)
    assert pipeline is not None
    model = RecoveryModel.train(events, seed=42)
    assert model.pipeline is not None


# ---------------------------------------------------------------------------
# Plan 02 — comparison, persistence, CLI
# ---------------------------------------------------------------------------


def test_train_compare_models_returns_metrics(events):
    result = compare_models(events, seed=42)
    assert "logistic" in result and "xgboost" in result
    assert result["selected_model"] in ("logistic", "xgboost")
    assert hasattr(result["pipeline"], "predict_proba")
    for name in ("logistic", "xgboost"):
        rec = result[name]
        assert {"roc_auc", "log_loss", "brier"} <= set(rec)
        assert 0.0 <= rec["roc_auc"] <= 1.0
        assert rec["log_loss"] >= 0.0
        assert 0.0 <= rec["brier"] <= 1.0


def test_xgboost_comparison_uses_same_feature_contract(events):
    frame = build_training_frame(events, seed=42)
    assert "segment" not in frame.columns
    assert "segment_encoded" not in frame.columns
    xgb_pipe = train_xgboost(events, seed=42)
    model = RecoveryModel(xgb_pipe)
    row = frame.iloc[0]
    prob = model.predict_proba(_features_from_row(row), "RETRY")
    assert 0.0 <= prob <= 1.0


def test_persistence_round_trip(events, tmp_path):
    result = compare_models(events, seed=42)
    model = RecoveryModel(result["pipeline"])
    path = tmp_path / "model.joblib"
    model.save(path, metrics=result)
    loaded = RecoveryModel.load(path)
    row = build_training_frame(events, seed=42).iloc[0]
    features = _features_from_row(row)
    for strategy in TRAINING_STRATEGIES:
        p1 = model.predict_proba(features, strategy)
        p2 = loaded.predict_proba(features, strategy)
        assert math.isclose(p1, p2, rel_tol=1e-9, abs_tol=1e-9)
        assert 0.0 <= p2 <= 1.0


def test_selected_model_prediction_is_deterministic(events):
    m1 = RecoveryModel(compare_models(events, seed=42)["pipeline"])
    m2 = RecoveryModel(compare_models(events, seed=42)["pipeline"])
    row = build_training_frame(events, seed=42).iloc[0]
    features = _features_from_row(row)
    for strategy in TRAINING_STRATEGIES:
        assert math.isclose(
            m1.predict_proba(features, strategy),
            m2.predict_proba(features, strategy),
            rel_tol=1e-9,
            abs_tol=1e-9,
        )


def test_load_rejects_malformed_artifact(tmp_path):
    bad = tmp_path / "bad.joblib"
    joblib.dump({"nope": 1}, bad)
    with pytest.raises(ValueError):
        RecoveryModel.load(bad)


def test_load_rejects_feature_mismatch(events, tmp_path):
    result = compare_models(events, seed=42)
    model = RecoveryModel(result["pipeline"], feature_columns=["a", "b"])
    path = tmp_path / "mismatch.joblib"
    model.save(path)
    with pytest.raises(ValueError):
        RecoveryModel.load(path)


def test_training_cli_smoke(tmp_path, monkeypatch):
    # Avoid writing JSON data fixtures from the CLI's generator call.
    monkeypatch.setattr(
        SyntheticDataGenerator, "_save", lambda self, dataset, n_events: None
    )
    output = tmp_path / "cli.joblib"
    subprocess.run(
        [
            sys.executable,
            "scripts/train_recovery_model.py",
            "--events",
            "200",
            "--seed",
            "42",
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert output.exists()
    loaded = RecoveryModel.load(output)
    events = SyntheticDataGenerator(seed=42).generate(200).events
    row = build_training_frame(events, seed=42).iloc[0]
    features = _features_from_row(row)
    for strategy in [
        "RETRY",
        "PAYMENT_METHOD_SWITCH",
        "WHATSAPP_REMINDER",
        "EMAIL_REMINDER",
        "DISCOUNT_OFFER",
    ]:
        prob = loaded.predict_proba(features, strategy)
        assert 0.0 <= prob <= 1.0
        assert math.isfinite(prob)
