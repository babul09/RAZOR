# Plan 02-02 Summary — XGBoost Comparison, Persistence & Training CLI

**Phase:** 02-ml-recovery-prediction-model · **Plan:** 02 · **Wave:** 2
**Status:** COMPLETE

## What was built

Completed the ML phase on top of the Plan 01 contract:

- **`ml/training.py`** (extended):
  - `train_xgboost()` — XGBoost `Pipeline` on the same 12-feature frame.
  - `compare_models()` — trains logistic + XGBoost on the same seeded holdout, reports ROC-AUC / log_loss / Brier, and deterministically selects the trusted model (higher ROC-AUC, tie-break lower log_loss; no hard-coded winner).
- **`ml/recovery_model.py`** (extended):
  - `RecoveryModel.save(path, metrics=None)` — writes a **versioned joblib envelope** (version, fitted pipeline, `FEATURE_COLUMNS`, aliases, canonical strategies, metrics, `trained_at`).
  - `RecoveryModel.load(path)` — validates version + required keys + exact feature-column equality; raises `ValueError` on malformed/mismatched artifacts.
- **`scripts/train_recovery_model.py`** — offline CLI with `--events` / `--seed` / `--output`; trains, selects, persists, prints metrics; no DB/Redis/Gemini/payment imports. Adds project root to `sys.path` for direct `python scripts/...` invocation.
- **`ml/artifacts/recovery_model.joblib`** — committed trusted deliverable (185 KB), XGBoost-selected.

## Verification

- `python -m pytest tests/test_recovery_model.py -q` → **13 passed**.
- `python -m pytest -q` (full suite) → **13 passed**.
- Production run `python scripts/train_recovery_model.py --events 20000 --seed 42`:
  - logistic  roc_auc=0.5641 log_loss=0.6773 brier=0.2422
  - xgboost   roc_auc=0.6098 log_loss=0.6443 brier=0.2272
  - **selected: xgboost**
- Loaded artifact emits finite `[0,1]` probabilities for all 5 canonical strategies and aliases; aliases equal canonical values.

## Deliverables

- `ml/training.py`, `ml/recovery_model.py`, `tests/test_recovery_model.py` (expanded)
- `scripts/train_recovery_model.py`
- `ml/artifacts/recovery_model.joblib` (reproducible, offline, trusted local)

## Threat mitigations

- T-02-04 (load tampering) — versioned envelope + required-key and feature-column validation, `ValueError` on malformed files.
- T-02-05 (training DoS) — offline, positive bounded event count, deterministic seed/output.
- T-02-06 (probability boundary) — `predict_proba` cast to float, finite `[0,1]` asserted after reload.
- T-02-SC (dependency) — only declared deps used; no new package install.
