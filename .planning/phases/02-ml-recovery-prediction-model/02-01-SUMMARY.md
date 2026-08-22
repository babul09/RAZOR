# Plan 02-01 Summary — Logistic Baseline & Prediction API

**Phase:** 02-ml-recovery-prediction-model · **Plan:** 01 · **Wave:** 1
**Status:** COMPLETE

## What was built

Established the stable Phase 2 feature and prediction contract, proven fully offline:

- **`ml/__init__.py`** — importable ML package marker.
- **`ml/training.py`** — owns the canonical Phase 2 contract:
  - `TRAINING_STRATEGIES` (5): `RETRY`, `PAYMENT_METHOD_SWITCH`, `WHATSAPP_REMINDER`, `EMAIL_REMINDER`, `DISCOUNT_OFFER`.
  - `FEATURE_COLUMNS` (exactly 12): `transaction_amount_paise`, `payment_method`, `failure_code`, `customer_ltv_paise`, `previous_successes`, `previous_failures`, `time_since_last_payment_days`, `historical_payment_hour`, `historical_payment_day`, `previous_strategy`, `previous_strategy_success_rate`, `candidate_strategy`.
  - `normalize_strategy()` — case-insensitive alias mapping (`METHOD_SWITCH`, `WHATSAPP`, `EMAIL`, `DISCOUNT`), rejects unsupported names with `ValueError`.
  - `build_training_frame()` — expands every event × 5 strategies into counterfactual rows with deterministic oracle labels; no `segment`/`segment_encoded` leakage.
  - `build_preprocessor()` (scaled numeric + one-hot categorical `ColumnTransformer`) and `train_logistic_regression()` (`Pipeline`).
- **`ml/recovery_model.py`** — `RecoveryModel` with `train()` and `predict_proba(features, strategy)`. Prediction builds one row without mutating the caller's mapping.
- **`tests/test_recovery_model.py`** — 6 focused tests covering feature shape, alias handling, probability bounds, paise boundary, and offline smoke.

## Verification

- `python -m pytest tests/test_recovery_model.py -q` → **6 passed**.
- Confirmed a 20,000-event frame expands to **100,000 strategy rows** with exactly 12 feature columns.

## Contracts locked for Phase 3

- `RecoveryModel.predict_proba(features: dict, strategy: str) -> float` in `[0, 1]`.
- 12-feature order in `FEATURE_COLUMNS`; money remains integer paise.

## Threat mitigations

- T-02-01 (strategy normalization) — allowlist + reject before inference.
- T-02-02 (segment leakage) — excluded + asserted in tests.
- T-02-03 (paise boundary) — integer inputs preserved + tested.
- T-02-SC (dependency) — only declared deps used.
