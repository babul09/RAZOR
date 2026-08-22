# Plan 03-02 Summary — Policy Engine + Outcome Verifier + Demo CLI

**Phase:** 03-decision-engine · **Plan:** 02 · **Wave:** 2
**Status:** COMPLETE

## What was built

Completed Phase 3 on top of the Wave 1 decision engine:

- **`engine/policy_engine.py`** — `MerchantPolicy` (7 guardrail fields + configurable WAIT window), `load_policy_yaml()` (defaults, malformed-file `ValueError`), `PolicyEngine.check()` enforcing all 7 checks as a hard gate → `PASS | APPROVAL_REQUIRED | BLOCK` (AC-05 discount block; WAIT/STOP pass).
- **`engine/policies/merchant_001.yaml`** — demo merchant policy.
- **`engine/outcome_verifier.py`** — `ActionExecutor` (simulator oracle, no real APIs) + `OutcomeVerifier.verify()` writing `RecoveryOutcome` and setting case `RECOVERED`/`FAILED` (FR-08/FR-10).
- **`scripts/demo_decision_engine.py`** — seed-DB CLI: loads/seeds cases, runs decide + policy, prints per-case table, proves AC-04 (WAIT) and AC-05 (discount BLOCK), all decisions logged (AC-08).
- **`tests/test_policy_engine.py`** — 11 tests (policy load/defaults, all checks, AC-05, outcome verifier, demo CLI smoke).

## Verification
- `python -m pytest tests/test_policy_engine.py -q` → **11 passed**.
- Full suite → **29 passed**.
- `python scripts/demo_decision_engine.py --limit 5` → exit 0; printed 1 WAIT case, `DISCOUNT_OFFER @25% -> BLOCK`, `@10% -> PASS`, `APPROVAL_REQUIRED` for high amounts.

## Dependencies
- Added `pyyaml>=6.0.0` to `pyproject.toml` + `requirements.txt` (declared before use).

## Notes
- Fixed: outcome verifier returned detached ORM instance — set `expire_on_commit=False`.
- Demo auto-creates `recovery_cases` from failed `payments` when none exist; `scripts/seed_db.py` is idempotent.
