# Phase 2: ML Recovery Prediction Model - Research

**Researched:** 2026-08-22
**Domain:** Python supervised binary classification for synthetic payment recovery strategy prediction
**Confidence:** MEDIUM

## User Constraints

No Phase 2 CONTEXT.md exists in `/home/kelvin/Documents/RAZOR/.planning/phases/02-ml-recovery-prediction-model`, so there are no additional locked decisions, discretion notes, or deferred ideas beyond REQUIREMENTS.md, STATE.md, ROADMAP.md, and the invocation prompt. [VERIFIED: gsd init.phase-op output, 2026-08-22]

## Summary

Phase 2 should implement a small, deterministic, offline Python ML layer that trains from Phase 1 synthetic events and exposes `ml/recovery_model.py` with a `.predict_proba(features, strategy)` API. The project has already locked the ML approach as "XGBoost + scikit-learn" and all-money-in-integer-paise constraints. [VERIFIED: .planning/STATE.md:17-27] Quote: "ML approach | XGBoost + scikit-learn" and "All money in integer paise (no floating point)".

The main planning issue is label availability. Phase 1 generates event features and the simulator has hidden segment/strategy probability rules, but no persisted supervised rows with `strategy` and `recovered` labels for every candidate strategy. [VERIFIED: simulation/generator.py:14-36] Quote: "transaction_amount_paise", "payment_method", "failure_code", "customer_ltv_paise", "previous_successes", "previous_failures", "days_since_last_payment", "historical_payment_hour", "historical_payment_day", "retry_success_rate", "whatsapp_success_rate", "email_success_rate", "upi_switch_success_rate". [VERIFIED: simulation/razor_simulator.py:10-16] Quote: `("A", "RETRY", True): 0.78`, `("B", "PAYMENT_METHOD_SWITCH", None): 0.81`, `("C", "WHATSAPP_REMINDER", None): 0.67`, `("D", "HUMAN_ESCALATION", None): 0.85`, `("E", None, None): 0.05`. The plan must add a training-data builder that expands each event across candidate strategies and generates deterministic binary outcomes from these oracle probabilities.

**Primary recommendation:** Use scikit-learn `Pipeline`/`ColumnTransformer` preprocessing, train one binary classifier over event features plus candidate strategy, compare `LogisticRegression` vs `xgboost.XGBClassifier`, persist the selected trusted artifact under `ml/artifacts/recovery_model.joblib`, and keep tests pure/offline with generated in-memory events. [CITED: https://scikit-learn.org/stable/modules/compose.html] [CITED: https://xgboost.readthedocs.io/en/stable/parameter.html] [CITED: https://scikit-learn.org/stable/model_persistence.html]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Synthetic training event generation | Python simulation layer | Filesystem JSON fixtures | Phase 1 owns deterministic event generation and writes JSON under `simulation/data/`. [VERIFIED: simulation/generator.py:45-99] |
| Feature engineering | ML layer | Simulation layer | `simulation/features.py` has reusable mappings, but Phase 2 needs strategy-aware feature rows and should centralize inference feature order in `ml/recovery_model.py`. [VERIFIED: simulation/features.py:8-36] |
| Model training and comparison | ML layer | CLI/script layer | Training is local/offline and should not require PostgreSQL. [VERIFIED: .planning/REQUIREMENTS.md:119-133] |
| Prediction API | ML layer | Future strategy engine | `.predict_proba(features, strategy)` is the deliverable API consumed by Phase 3 expected-net-recovery logic. [VERIFIED: .planning/ROADMAP.md:25-34] |
| Persistence | ML layer | Filesystem | Persist fitted preprocessing plus estimator together so prediction uses identical transformations. [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.pipeline.Pipeline.html] |
| Validation | Tests | ML layer | Unit tests must verify all required strategy names return valid probabilities without a database. [VERIFIED: .planning/ROADMAP.md:30-34] |

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FR-05 | Recovery Prediction Model: synthetic 20,000-event training data, listed features, `P(recovery \| strategy)`, logistic regression and XGBoost acceptable. | Use Phase 1 generator, candidate-strategy row expansion, scikit-learn baseline, XGBoost comparison. [VERIFIED: .planning/REQUIREMENTS.md:33-38] |
| NFR-02 | Simulation of 10,000 events completes in less than 60 seconds. | Keep model inference vectorized for simulation and train/predict offline; avoid DB and network in prediction. [VERIFIED: .planning/REQUIREMENTS.md:114-119] |
| NFR-03 | All money arithmetic uses integer paise. | Keep amount/LTV as integer paise inputs; only model probabilities and metrics use floats. [VERIFIED: db/models.py:1-6] Quote: "All monetary amounts stored as INTEGER PAISE (1 rupee = 100 paise). NEVER use Float for money." |
| NFR-06 | System works fully offline in simulator mode. | Training and tests should use `SyntheticDataGenerator` and local artifacts only. [VERIFIED: .planning/REQUIREMENTS.md:119] |
| Synthetic Dataset Requirements | 20,000 training events; five behavioral segments with deliberate ML patterns; listed customer features. | Keep hidden `segment` out of model features to avoid direct synthetic-label leakage, but use it for deterministic label generation. [VERIFIED: .planning/REQUIREMENTS.md:124-134] |
| AC-03 | ML model outputs per-strategy recovery probability for any input. | Normalize aliases and produce probabilities for RETRY, METHOD_SWITCH/PAYMENT_METHOD_SWITCH, WHATSAPP, EMAIL, DISCOUNT at minimum. [VERIFIED: .planning/REQUIREMENTS.md:154] |

## Project Constraints (from AGENTS.md)

No `./AGENTS.md` or `./.codex/AGENTS.md` was found during project discovery, so there are no project-specific AGENTS directives to list. [VERIFIED: `find . -maxdepth 3 ... AGENTS.md`, 2026-08-22]

No `.codex/skills/` or `.agents/skills/` project skill directories were found, so there are no project-local skill rules to incorporate. [VERIFIED: `find . -maxdepth 3 ... SKILL.md`, 2026-08-22]

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `scikit-learn` | declared `>=1.5.0`; latest observed `1.9.0` via `pip index versions` | Pipeline, preprocessing, train/test split, metrics, logistic baseline | Existing project dependency and official docs support `Pipeline`, `ColumnTransformer`, and `LogisticRegression`. [VERIFIED: pyproject.toml:12-14] [CITED: https://scikit-learn.org/stable/modules/compose.html] |
| `xgboost` | declared `>=2.0.0`; latest observed `3.4.1` via `pip index versions` | Gradient-boosted tree candidate model | Existing project dependency and project decision says XGBoost is preferred. [VERIFIED: pyproject.toml:13-14] [VERIFIED: .planning/STATE.md:17] [CITED: https://xgboost.readthedocs.io/en/stable/parameter.html] |
| `pandas` | declared `>=2.2.0`; latest observed `3.0.5` via `pip index versions` | DataFrame construction for training/evaluation | Existing `simulation/features.py` already returns a pandas DataFrame. [VERIFIED: pyproject.toml:12-13] [VERIFIED: simulation/features.py:35-36] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `numpy` | installed `2.5.2`; latest observed `2.5.2` via `pip index versions` | Deterministic RNG and numeric arrays | Existing generator and simulators use `np.random.default_rng(seed)`. [VERIFIED: simulation/generator.py:57-61] [VERIFIED: simulation/razor_simulator.py:43-45] |
| `joblib` | latest observed `1.5.3` via `pip index versions`; transitive through scikit-learn is likely but direct dependency is not declared [ASSUMED] | Persist fitted pipeline/artifact | Use for trusted local model artifacts; loading can execute code because it uses pickle protocol. [CITED: https://scikit-learn.org/stable/model_persistence.html] |
| `pytest` | declared `>=8.2.0`; latest observed `9.1.1` via `pip index versions` | Unit tests | Existing dependency but not installed in current interpreter. [VERIFIED: pyproject.toml:24] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `joblib` artifact | `pickle` stdlib | No extra dependency, but scikit-learn docs specifically identify joblib for performance/memory-mapped model loading when that matters. [CITED: https://scikit-learn.org/stable/model_persistence.html] |
| Single candidate-strategy classifier | One model per strategy | Per-strategy models are simple but duplicate preprocessing/training and make AC-03 alias handling more complex. [ASSUMED] |
| Include `segment_encoded` as feature | Exclude segment from model features | Including segment would inflate demo metrics because segment directly drives synthetic outcome probabilities; exclude it from model input and use it only for synthetic labels. [VERIFIED: simulation/features.py:14-31] [VERIFIED: simulation/razor_simulator.py:10-16] |

**Installation:**

```bash
pip install -e .
```

If the plan adds direct `joblib` dependency, add it to both `pyproject.toml` and `requirements.txt` only after a package-legitimacy checkpoint, because the seam timed out in this session. [ASSUMED]

## Package Legitimacy Audit

The Package Legitimacy Gate command `gsd_run query package-legitimacy check --ecosystem pypi scikit-learn xgboost pandas joblib pytest faker` timed out twice, including a 20-second hard timeout, so no `OK`/`SUS`/`SLOP` verdict was available. [VERIFIED: command output, 2026-08-22] Registry existence/current versions were verified with `pip index versions`, but that does not satisfy the GSD package legitimacy rule by itself.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `scikit-learn` | PyPI | not obtained | not obtained | not obtained | UNKNOWN | Already declared; planner should not treat as newly approved by this audit. |
| `xgboost` | PyPI | not obtained | not obtained | not obtained | UNKNOWN | Already declared; planner should not treat as newly approved by this audit. |
| `pandas` | PyPI | not obtained | not obtained | not obtained | UNKNOWN | Already declared; planner should not treat as newly approved by this audit. |
| `joblib` | PyPI | not obtained | not obtained | not obtained | UNKNOWN | If added as direct dependency, planner must add `checkpoint:human-verify`. |
| `pytest` | PyPI | not obtained | not obtained | not obtained | UNKNOWN | Already declared; planner should not treat as newly approved by this audit. |
| `faker` | PyPI | not obtained | not obtained | not obtained | UNKNOWN | Already declared for Phase 1 generator. [VERIFIED: pyproject.toml:24-25] |

**Packages removed due to [SLOP] verdict:** none; no SLOP verdict was returned.
**Packages flagged as suspicious [SUS]:** none; no SUS verdict was returned.

## Architecture Patterns

### System Architecture Diagram

```text
SyntheticDataGenerator(seed=42, n=20_000)
  -> EventRecord list
  -> candidate row expansion for each strategy
      -> strategy alias normalization
      -> synthetic oracle probability lookup
      -> seeded binary recovered label
  -> train/test split, stratified by label
      -> scikit-learn Pipeline/ColumnTransformer
          -> LogisticRegression baseline
          -> XGBClassifier challenger
      -> metric comparison: ROC-AUC, log_loss, Brier score, probability bounds
  -> select model
  -> persist trusted artifact
  -> RecoveryModel.predict_proba(features, strategy)
      -> normalized strategy
      -> one-row DataFrame
      -> pipeline.predict_proba
      -> float probability in [0, 1]
```

### Recommended Project Structure

```text
ml/
├── __init__.py
├── recovery_model.py          # public RecoveryModel API, normalization, artifact load/save
├── training.py                # build_training_frame, train_baseline, train_xgboost, compare
└── artifacts/
    └── recovery_model.joblib  # generated trusted local model artifact, git-ignore if large

tests/
└── test_recovery_model.py     # offline probability/API/normalization tests
```

### Pattern 1: Candidate-Strategy Training Rows

**What:** Expand every event into one row per candidate strategy so a single binary classifier learns `P(recovered | event_features, candidate_strategy)`. [ASSUMED]

**When to use:** Required for AC-03 because Phase 2 must return probabilities for all strategies, not just the simulator-selected one. [VERIFIED: .planning/REQUIREMENTS.md:154]

**Example:**

```python
# Source: in-repo strategy values and oracle probabilities.
# RecoveryStrategy quote: "RETRY", "PAYMENT_METHOD_SWITCH", "WHATSAPP_REMINDER",
# "EMAIL_REMINDER", "DISCOUNT_OFFER". [VERIFIED: db/models.py:39-48]
TRAINING_STRATEGIES = [
    "RETRY",
    "PAYMENT_METHOD_SWITCH",
    "WHATSAPP_REMINDER",
    "EMAIL_REMINDER",
    "DISCOUNT_OFFER",
]
```

### Pattern 2: Keep Preprocessing in Pipeline

**What:** Use `Pipeline` with preprocessing and the estimator in one fitted object. scikit-learn docs state that pipeline prediction transforms data through intermediate steps before calling the final estimator. [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.pipeline.Pipeline.html]

**When to use:** Always for train/test evaluation, persistence, and inference to avoid training-serving skew.

**Example:**

```python
# Source: scikit-learn Pipeline and ColumnTransformer docs.
pipeline = Pipeline([
    ("preprocess", preprocessor),
    ("model", LogisticRegression(max_iter=1000, random_state=42)),
])
```

### Pattern 3: Strategy Alias Normalization at API Boundary

**What:** Accept hackathon shorthand names and map them to canonical `RecoveryStrategy` values before model prediction.

**Canonical quote:** `RecoveryStrategy` values are `"RETRY"`, `"PAYMENT_METHOD_SWITCH"`, `"WHATSAPP_REMINDER"`, `"EMAIL_REMINDER"`, `"PAYMENT_LINK"`, `"DISCOUNT_OFFER"`, `"HUMAN_ESCALATION"`, `"WAIT"`, `"STOP"`. [VERIFIED: db/models.py:39-48]

**Phase 2 aliases:** `METHOD_SWITCH -> PAYMENT_METHOD_SWITCH`, `WHATSAPP -> WHATSAPP_REMINDER`, `EMAIL -> EMAIL_REMINDER`, `DISCOUNT -> DISCOUNT_OFFER`. [ASSUMED]

**Future Phase 3 handling:** `PAYMENT_LINK`, `HUMAN_ESCALATION`, `WAIT`, and `STOP` are canonical strategy enum values but are outside the Phase 2 required probability set unless the planner explicitly extends training labels for them. [VERIFIED: db/models.py:39-48]

### Anti-Patterns to Avoid

- **Training on only selected simulator actions:** It leaves no evidence for alternate strategies and fails AC-03 for arbitrary per-strategy probabilities. [ASSUMED]
- **Using `segment_encoded` as an inference feature:** It is a synthetic hidden segment and directly controls simulator probabilities; using it in inference would overfit the demo. [VERIFIED: simulation/features.py:14-31] [VERIFIED: simulation/razor_simulator.py:10-16]
- **Fitting preprocessing before train/test split:** scikit-learn documents this as a leakage risk and recommends pipelines for cross-validation/tuning. [CITED: https://scikit-learn.org/stable/common_pitfalls.html]
- **Loading arbitrary joblib/pickle artifacts:** scikit-learn docs warn pickle-protocol formats can execute arbitrary code on load. [CITED: https://scikit-learn.org/stable/model_persistence.html]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Logistic baseline | Manual sigmoid/gradient descent | `sklearn.linear_model.LogisticRegression` | Official estimator has regularization, solvers, and `predict_proba`. [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html] |
| Preprocessing orchestration | Ad hoc fit/transform functions | `Pipeline` + `ColumnTransformer` | Official docs identify pipelines as a way to compose transforms and avoid leakage in cross-validation. [CITED: https://scikit-learn.org/stable/modules/compose.html] |
| Gradient-boosted trees | Custom tree boosting | `xgboost.XGBClassifier` | XGBoost supports probability-producing binary classification objectives. [CITED: https://xgboost.readthedocs.io/en/stable/parameter.html] |
| Model serialization | Custom JSON of estimator internals | `joblib` or `pickle` for trusted local artifacts | scikit-learn docs cover these persistence options and their security constraints. [CITED: https://scikit-learn.org/stable/model_persistence.html] |
| Test data source | PostgreSQL fixtures | In-memory `SyntheticDataGenerator(seed=...)` | Phase 2 must work offline and the generator is deterministic. [VERIFIED: simulation/generator.py:57-63] [VERIFIED: .planning/REQUIREMENTS.md:119] |

**Key insight:** The complex part is not model math; it is producing non-leaky, strategy-aware supervised rows from the synthetic simulator while keeping the public API stable for Phase 3. [ASSUMED]

## Common Pitfalls

### Pitfall 1: No Counterfactual Labels

**What goes wrong:** Training on the single strategy selected by `select_strategy()` cannot answer "what if EMAIL instead of RETRY?" for the same event. [ASSUMED]

**Why it happens:** Phase 1 simulator chooses one strategy per event. [VERIFIED: simulation/razor_simulator.py:25-36]

**How to avoid:** Build training data as event x candidate_strategy rows with synthetic labels from the same oracle probability table used by the simulator.

**Warning signs:** Tests only check the selected strategy; model returns a constant/default for unsupported strategies.

### Pitfall 2: Strategy Name Drift

**What goes wrong:** Roadmap shorthand uses `METHOD_SWITCH`, `WHATSAPP`, `EMAIL`, `DISCOUNT`, while DB enum values use longer canonical names. [VERIFIED: .planning/ROADMAP.md:30] [VERIFIED: db/models.py:39-48]

**How to avoid:** Implement a single `normalize_strategy()` and use it in training, prediction, and tests.

**Warning signs:** Duplicate feature rows for `METHOD_SWITCH` and `PAYMENT_METHOD_SWITCH`, or tests hard-code only one naming style.

### Pitfall 3: Leakage Through Synthetic Segment

**What goes wrong:** `segment_encoded` makes the model learn the generator's hidden answer rather than realistic observable behavior. [VERIFIED: simulation/features.py:14-31]

**How to avoid:** Exclude `segment`/`segment_encoded` from inference features; use segment only to generate labels and stratify/debug metrics.

**Warning signs:** Near-perfect test AUC on 20,000 synthetic events without meaningful feature engineering.

### Pitfall 4: Money as Float

**What goes wrong:** Amount/LTV converted to rupees floats can violate NFR-03 and diverge from DB schema.

**How to avoid:** Keep `transaction_amount_paise` and `customer_ltv_paise` as integer columns; scaling inside ML preprocessing is acceptable because it is not money arithmetic. [VERIFIED: db/models.py:1-6]

**Warning signs:** Feature API takes `transaction_amount` in rupees without a clear conversion boundary.

### Pitfall 5: Persistence Without Version Envelope

**What goes wrong:** A raw pickle/joblib file cannot tell the loader which feature order, strategy mapping, or library versions produced it. [ASSUMED]

**How to avoid:** Persist an artifact dict with `model`, `feature_columns`, `strategy_aliases`, `metrics`, and `trained_at`.

**Warning signs:** `joblib.load(path).predict_proba(...)` is called directly across the codebase.

## Code Examples

Verified patterns from official sources and in-repo definitions:

### Public API Skeleton

```python
# Source: ROADMAP deliverable and db RecoveryStrategy enum.
class RecoveryModel:
    def predict_proba(self, features: dict, strategy: str) -> float:
        canonical = normalize_strategy(strategy)
        row = build_prediction_row(features, canonical)
        probabilities = self.pipeline.predict_proba(row)
        return float(probabilities[0, 1])
```

### Strategy Normalization Table

```python
# Source canonical values quote:
# "RETRY", "PAYMENT_METHOD_SWITCH", "WHATSAPP_REMINDER", "EMAIL_REMINDER",
# "PAYMENT_LINK", "DISCOUNT_OFFER", "HUMAN_ESCALATION", "WAIT", "STOP".
# [VERIFIED: db/models.py:39-48]
STRATEGY_ALIASES = {
    "RETRY": "RETRY",
    "METHOD_SWITCH": "PAYMENT_METHOD_SWITCH",
    "PAYMENT_METHOD_SWITCH": "PAYMENT_METHOD_SWITCH",
    "WHATSAPP": "WHATSAPP_REMINDER",
    "WHATSAPP_REMINDER": "WHATSAPP_REMINDER",
    "EMAIL": "EMAIL_REMINDER",
    "EMAIL_REMINDER": "EMAIL_REMINDER",
    "DISCOUNT": "DISCOUNT_OFFER",
    "DISCOUNT_OFFER": "DISCOUNT_OFFER",
}
```

### Feature Columns

```python
# Source FR-05 feature names and Phase 2 target count.
# FR-05 quote: "transaction_amount, payment_method, failure_code, customer_ltv,
# previous_successes, previous_failures, time_since_last_payment,
# historical_payment_hour, historical_payment_day, previous_strategy,
# previous_strategy_success_rate". [VERIFIED: .planning/REQUIREMENTS.md:33-38]
FEATURE_COLUMNS = [
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
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual preprocessing outside model | `Pipeline`/`ColumnTransformer` with estimator | Current scikit-learn stable docs | Reduces leakage and keeps persisted preprocessing/inference consistent. [CITED: https://scikit-learn.org/stable/modules/compose.html] |
| Pickle/joblib without trust boundary | Treat persisted artifacts as trusted local files only, or use safer formats for untrusted artifacts | Current scikit-learn stable docs | Prevents unsafe loading of attacker-controlled model files. [CITED: https://scikit-learn.org/stable/model_persistence.html] |
| Selected-action-only simulation labels | Event x strategy counterfactual training rows | Phase 2 design need | Enables AC-03 per-strategy probability output. [ASSUMED] |

**Deprecated/outdated:**
- `sklearn.externals.joblib`: do not use; import `joblib` directly if using joblib. [ASSUMED]
- `multi:softmax` for probability outputs in XGBoost: XGBoost docs say multiclass AUC probability use should use `multi:softprob`, not `multi:softmax`. [CITED: https://xgboost.readthedocs.io/en/stable/parameter.html]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Use one binary classifier with `candidate_strategy` instead of one model per strategy. | Standard Stack / Architecture Patterns | Planner may need to change training shape if per-strategy independent models are preferred. |
| A2 | Add `candidate_strategy` as the 12th compatibility feature. | Code Examples | If the user intended a different 12th feature, API and training rows need adjustment. |
| A3 | Exclude `segment_encoded` from model features to avoid synthetic leakage. | Pitfalls | Demo metrics may be lower but more credible; including it would be easier. |
| A4 | Importing/using `joblib` is acceptable if installed transitively by scikit-learn or after direct dependency verification. | Standard Stack | Direct dependency may need an explicit human verification checkpoint. |
| A5 | `sklearn.externals.joblib` should not be used. | State of the Art | Low risk; planner can verify during implementation if needed. |

## Open Questions

1. **Should the persisted model artifact be committed?**
   - What we know: Roadmap requires model persistence. [VERIFIED: .planning/ROADMAP.md:31]
   - What's unclear: Whether generated `ml/artifacts/recovery_model.joblib` should live in git or be generated by a training command.
   - Recommendation: Keep training reproducible and commit code/tests; commit artifact only if hackathon demo startup speed requires it. [ASSUMED]

2. **Should Phase 2 support Phase 3 strategies now?**
   - What we know: Phase 3 strategy enum includes `PAYMENT_LINK`, `HUMAN_ESCALATION`, `WAIT`, and `STOP`. [VERIFIED: db/models.py:39-48]
   - What's unclear: Phase 2 roadmap only requires RETRY, METHOD_SWITCH, WHATSAPP, EMAIL, DISCOUNT. [VERIFIED: .planning/ROADMAP.md:30]
   - Recommendation: Normalize future names but return `ValueError` or configured fallback for unsupported probability strategies until Phase 3 extends labels. [ASSUMED]

3. **What metric threshold is good enough for demo?**
   - What we know: FR-05 asks for comparison, not a numeric AUC/log-loss threshold. [VERIFIED: .planning/REQUIREMENTS.md:33-38]
   - What's unclear: Acceptance criteria do not define model-quality gates.
   - Recommendation: Gate on valid probability outputs for all strategies plus XGBoost beating logistic regression on ROC-AUC or log-loss; report metrics without blocking if improvement is small. [ASSUMED]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Training/tests | yes | 3.14.7 | Use project-supported Python >=3.11. [VERIFIED: pyproject.toml:5] |
| pip | Installing declared deps | yes | 26.2.1 | `python -m pip` |
| numpy | Generator/simulator | yes | 2.5.2 | none needed locally |
| pandas | Feature DataFrame/training | no in current interpreter | — | `pip install -e .` |
| scikit-learn | Baseline, preprocessing, metrics | no in current interpreter | — | `pip install -e .` |
| xgboost | Challenger model | no in current interpreter | — | Defer XGBoost training or use logistic baseline only until install |
| joblib | Persistence | no in current interpreter | — | stdlib `pickle` for trusted local demo artifact |
| pytest | Unit tests | no in current interpreter | — | Install declared project deps |
| PostgreSQL | Not required for Phase 2 tests | not probed | — | Use generator and JSON fixtures only |

**Missing dependencies with no fallback:**
- `pandas` and `scikit-learn` block full Phase 2 implementation/tests until project dependencies are installed. [VERIFIED: local `python -c importlib.metadata`, 2026-08-22]

**Missing dependencies with fallback:**
- `xgboost`: logistic regression baseline can be implemented first; XGBoost comparison requires install.
- `joblib`: stdlib `pickle` can persist trusted artifacts if direct joblib use is deferred.
- `pytest`: tests cannot run until installed, but test files can still be planned.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest declared `>=8.2.0`, latest observed `9.1.1`; not installed locally. [VERIFIED: pyproject.toml:24] |
| Config file | none found |
| Quick run command | `python -m pytest tests/test_recovery_model.py -q` |
| Full suite command | `python -m pytest -q` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FR-05 | Training frame has 12 feature columns and includes event x strategy rows. | unit | `python -m pytest tests/test_recovery_model.py::test_training_frame_has_required_features -q` | no, Wave 0 |
| FR-05 | Logistic and XGBoost training produce comparable metric dicts. | unit | `python -m pytest tests/test_recovery_model.py::test_train_compare_models_returns_metrics -q` | no, Wave 0 |
| AC-03 | `.predict_proba(features, strategy)` returns float in `[0, 1]` for all Phase 2 aliases. | unit | `python -m pytest tests/test_recovery_model.py::test_predict_proba_all_phase2_strategies -q` | no, Wave 0 |
| NFR-03 | Feature builder preserves paise integer inputs at API boundary. | unit | `python -m pytest tests/test_recovery_model.py::test_money_features_remain_paise_inputs -q` | no, Wave 0 |
| NFR-06 | Tests/train smoke use generator only, no PostgreSQL imports/session. | unit | `python -m pytest tests/test_recovery_model.py::test_training_smoke_offline -q` | no, Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_recovery_model.py -q`
- **Per wave merge:** `python -m pytest -q`
- **Phase gate:** Full suite green before `$gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_recovery_model.py` - covers FR-05, AC-03, NFR-03, NFR-06
- [ ] `ml/__init__.py` - importable ML package
- [ ] Framework install: `pip install -e .` - local interpreter currently lacks declared ML/test dependencies

## Security Domain

Security enforcement is enabled by default because `.planning/config.json` does not set `security_enforcement: false`. [VERIFIED: .planning/config.json:1-48]

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface in Phase 2; offline local ML code. [ASSUMED] |
| V3 Session Management | no | No sessions in Phase 2. [ASSUMED] |
| V4 Access Control | no | No user-facing authorization boundary in Phase 2. [ASSUMED] |
| V5 Input Validation | yes | Validate strategy names, required feature keys, numeric ranges, and reject unknown categorical values or map to explicit `UNKNOWN`. [ASSUMED] |
| V6 Cryptography | yes, for persistence trust boundary | Do not load untrusted pickle/joblib artifacts; scikit-learn docs warn loading can execute arbitrary code. [CITED: https://scikit-learn.org/stable/model_persistence.html] |

### Known Threat Patterns for Python ML Artifact Loading

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Untrusted pickle/joblib artifact execution | Elevation of privilege | Load only trusted local artifacts generated by project training code; never accept model file uploads or remote model paths. [CITED: https://scikit-learn.org/stable/model_persistence.html] |
| Malformed strategy names causing silent fallback | Tampering | Normalize through a strict alias table and raise on unsupported values. [ASSUMED] |
| Training/inference feature mismatch | Tampering | Persist feature columns and strategy aliases with the model artifact; tests assert order and required keys. [ASSUMED] |
| Float money arithmetic creeping into business logic | Tampering | Keep money values in paise at API boundaries; probabilities may be float, money remains int. [VERIFIED: db/models.py:1-6] |

## Sources

### Primary (HIGH confidence)

- `.planning/REQUIREMENTS.md` - FR-05, NFR-02/NFR-03/NFR-06, synthetic dataset requirements, AC-03. [VERIFIED: .planning/REQUIREMENTS.md:33-38] [VERIFIED: .planning/REQUIREMENTS.md:114-119] [VERIFIED: .planning/REQUIREMENTS.md:124-154]
- `.planning/STATE.md` - project decisions: XGBoost + scikit-learn, integer paise, offline/simulation emphasis. [VERIFIED: .planning/STATE.md:12-29]
- `.planning/ROADMAP.md` - Phase 2 deliverable and required strategy set. [VERIFIED: .planning/ROADMAP.md:25-34]
- `db/models.py` - canonical strategy enum and money schema comments. [VERIFIED: db/models.py:1-6] [VERIFIED: db/models.py:39-48]
- `simulation/generator.py` - generated event fields, segments, seed behavior, JSON output paths. [VERIFIED: simulation/generator.py:14-36] [VERIFIED: simulation/generator.py:45-63] [VERIFIED: simulation/generator.py:147-155]
- `simulation/features.py` - existing feature mappings and DataFrame builder. [VERIFIED: simulation/features.py:8-36]
- `simulation/razor_simulator.py` - oracle recovery probabilities and strategy costs/selection behavior. [VERIFIED: simulation/razor_simulator.py:10-36]
- `pyproject.toml` and `requirements.txt` - declared Python dependencies. [VERIFIED: pyproject.toml:5-26] [VERIFIED: requirements.txt:1-19]

### Secondary (MEDIUM confidence)

- scikit-learn Pipeline docs - prediction flows through transforms to final estimator `predict_proba`. [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.pipeline.Pipeline.html]
- scikit-learn pipelines/composite estimators docs - Pipeline and ColumnTransformer composition and leakage reduction. [CITED: https://scikit-learn.org/stable/modules/compose.html]
- scikit-learn common pitfalls docs - leakage definition and prevention. [CITED: https://scikit-learn.org/stable/common_pitfalls.html]
- scikit-learn LogisticRegression docs - regularized logistic classifier and solver behavior. [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html]
- scikit-learn model persistence docs - joblib/pickle tradeoffs and arbitrary code execution warning. [CITED: https://scikit-learn.org/stable/model_persistence.html]
- XGBoost prediction and parameter docs - `predict_proba` and probability-producing binary objective. [CITED: https://xgboost.readthedocs.io/en/stable/prediction.html] [CITED: https://xgboost.readthedocs.io/en/stable/parameter.html]

### Tertiary (LOW confidence)

- Package legitimacy verdicts are unavailable because the GSD legitimacy seam timed out; registry versions came from `pip index versions` only.
- Design choices marked `[ASSUMED]` need planner/user confirmation before becoming locked implementation decisions.

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM - package names are project-declared and registry versions were checked, but the package-legitimacy seam timed out.
- Architecture: HIGH for in-repo integration points, MEDIUM for recommended training-row design because labels are not yet implemented.
- Pitfalls: MEDIUM - leakage/persistence risks are documented by official scikit-learn docs; counterfactual-label risk is inferred from current simulator shape.

**Research date:** 2026-08-22
**Valid until:** 2026-09-21 for in-repo architecture; 2026-09-05 for current package versions.
