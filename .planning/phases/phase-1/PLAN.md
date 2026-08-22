# Phase 1 · Data & Simulation Foundation

## Objective
Build the synthetic dataset generator + simulators so that running `python simulate.py` outputs a ₹ recovered vs baseline comparison table. **No UI. Pure Python scripts.** This is the foundation everything else builds on — the ₹ numbers must be convincing before any other layer is built.

## Context
- **Project**: RAZOR — Revenue AI Zero-loss Operations and Recovery
- **Stack**: Python 3.11 + SQLAlchemy 2.x + PostgreSQL + pandas + scikit-learn + XGBoost
- **Currency**: ₹ INR — ALL amounts stored and computed as **integer paise** (₹1 = 100 paise). Never use float for money.
- **Hackathon**: Solo build. Pragmatic over perfect.
- **Seed**: All random operations seeded with `--seed` arg (default 42) for reproducibility.

---

## Wave 1 · Project Setup & DB Foundation
> These tasks are independent and can be done in parallel.

### Task 1.1 · `pyproject.toml` + `requirements.txt`
**File**: `pyproject.toml`, `requirements.txt`

**Dependencies** (include all — phases 2+ need them too):
```toml
[project]
name = "razor"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.30.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.13.0",
    "psycopg2-binary>=2.9.9",
    "pandas>=2.2.0",
    "scikit-learn>=1.5.0",
    "xgboost>=2.0.0",
    "google-generativeai>=0.7.0",
    "celery>=5.4.0",
    "redis>=5.0.0",
    "python-dotenv>=1.0.0",
    "rich>=13.7.0",
    "tabulate>=0.9.0",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.3.0",
    "httpx>=0.27.0",
    "pytest>=8.2.0",
    "faker>=25.0.0",
]
```

**Acceptance**: `pip install -e .` (or `pip install -r requirements.txt`) completes without error.

---

### Task 1.2 · `.env.example` + `config.py`
**Files**: `.env.example`, `config.py`

**.env.example**:
```
DATABASE_URL=postgresql://razor:razor@localhost:5432/razor_db
REDIS_URL=redis://localhost:6379/0
GEMINI_API_KEY=your_gemini_api_key_here
SECRET_KEY=change_me_in_production
ENVIRONMENT=development
```

**`config.py`** — Pydantic settings:
```python
class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    gemini_api_key: str = ""
    secret_key: str = "dev-secret"
    environment: str = "development"

    model_config = SettingsConfig(env_file=".env")

settings = Settings()
```

**Acceptance**: `from config import settings; print(settings.environment)` prints "development".

---

### Task 1.3 · `db/base.py` + `db/database.py`
**Files**: `db/__init__.py`, `db/base.py`, `db/database.py`

**`db/base.py`**:
```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

**`db/database.py`**:
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Acceptance**: `from db.database import engine, get_db` imports cleanly.

---

### Task 1.4 · `db/models.py` — All ORM Models
**File**: `db/models.py`

Define all models with these exact table names and column types. **All money columns end in `_paise` and are `BigInteger`.**

```python
# Enums
class RecoveryCaseStatus(str, enum.Enum):
    NEW = "NEW"
    DIAGNOSING = "DIAGNOSING"
    PREDICTED = "PREDICTED"
    STRATEGY_SELECTED = "STRATEGY_SELECTED"
    POLICY_CHECK = "POLICY_CHECK"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    RECOVERED = "RECOVERED"
    FAILED = "FAILED"
    STOPPED = "STOPPED"

class RecoveryStrategy(str, enum.Enum):
    RETRY = "RETRY"
    PAYMENT_METHOD_SWITCH = "PAYMENT_METHOD_SWITCH"
    WHATSAPP_REMINDER = "WHATSAPP_REMINDER"
    EMAIL_REMINDER = "EMAIL_REMINDER"
    PAYMENT_LINK = "PAYMENT_LINK"
    DISCOUNT_OFFER = "DISCOUNT_OFFER"
    HUMAN_ESCALATION = "HUMAN_ESCALATION"
    WAIT = "WAIT"
    STOP = "STOP"

class CustomerSegment(str, enum.Enum):
    A = "A"  # retry/evening
    B = "B"  # UPI switch
    C = "C"  # WhatsApp
    D = "D"  # human escalation
    E = "E"  # stop/abandon
```

**Models** (abbreviated — implement fully):
```
Merchant:           id (UUID PK), name, created_at
Customer:           id (UUID PK), merchant_id (FK), name, email, phone,
                    lifetime_value_paise (BigInt), preferred_payment_method,
                    typical_payment_hour_start (Int), typical_payment_hour_end (Int),
                    customer_segment (Enum), created_at
Payment:            id (UUID PK), merchant_id (FK), customer_id (FK),
                    amount_paise (BigInt), currency (default "INR"),
                    payment_method, status, failure_code, failure_reason,
                    created_at, updated_at
PaymentAttempt:     id (UUID PK), payment_id (FK), attempt_number,
                    status, failure_code, attempted_at
RecoveryCase:       id (UUID PK), merchant_id (FK), customer_id (FK),
                    source_type, source_id,
                    amount_at_risk_paise (BigInt), failure_code, failure_reason,
                    recovery_probability (Float), expected_recovery_value_paise (BigInt),
                    status (Enum RecoveryCaseStatus, default NEW),
                    priority (Int, computed), created_at, updated_at
CustomerRecoveryProfile:
                    id (UUID PK), customer_id (FK unique), merchant_id (FK),
                    retry_attempts (Int default 0), retry_successes (Int default 0),
                    whatsapp_attempts (Int default 0), whatsapp_successes (Int default 0),
                    email_attempts (Int default 0), email_successes (Int default 0),
                    upi_switch_attempts (Int default 0), upi_switch_successes (Int default 0),
                    discount_attempts (Int default 0), discount_successes (Int default 0),
                    overall_recovery_probability (Float default 0.5),
                    updated_at
RecoveryAction:     id (UUID PK), case_id (FK), strategy (Enum RecoveryStrategy),
                    status, cost_paise (BigInt), executed_at, completed_at, outcome
AgentDecision:      id (UUID PK), case_id (FK),
                    input_json (JSONB), strategies_evaluated_json (JSONB),
                    selected_strategy (Enum RecoveryStrategy),
                    reasoning (Text), policy_check_passed (Bool),
                    created_at
RecoveryOutcome:    id (UUID PK), case_id (FK), action_id (FK nullable),
                    revenue_recovered_paise (BigInt), cost_of_recovery_paise (BigInt),
                    net_revenue_recovered_paise (BigInt),
                    recovery_method (Enum RecoveryStrategy),
                    recovered_at
Experiment:         id (UUID PK), merchant_id (FK), name, status,
                    config_json (JSONB), created_at
ExperimentArm:      id (UUID PK), experiment_id (FK), arm_name,
                    traffic_percent (Float), strategy (Enum RecoveryStrategy),
                    attempts (Int default 0), recoveries (Int default 0),
                    revenue_recovered_paise (BigInt default 0)
AuditLog:           id (UUID PK), case_id (FK nullable), event_type (String),
                    details_json (JSONB), created_at
Policy:             id (UUID PK), merchant_id (FK unique),
                    max_discount_percent (Int default 10),
                    max_automated_amount_paise (BigInt default 500000),
                    max_contacts_count (Int default 3),
                    max_contacts_window_days (Int default 7),
                    require_human_approval_above_paise (BigInt default 500000),
                    allowed_channels (JSONB, default ["whatsapp","email"]),
                    stop_if_payment_succeeds (Bool default True)
```

Use `uuid.uuid4` as default for all PK columns. Use `datetime.utcnow` for timestamps.

**Acceptance**: `python -c "from db.models import Merchant, RecoveryCase, Policy"` imports cleanly.

---

### Task 1.5 · Alembic Setup + Initial Migration
**Files**: `alembic.ini`, `alembic/env.py`, `alembic/versions/001_initial_schema.py`

**`alembic.ini`**: Set `script_location = alembic`, `sqlalchemy.url = %(DATABASE_URL)s` (read from env).

**`alembic/env.py`**: Import `Base` from `db.base` and all models from `db.models`. Set `target_metadata = Base.metadata`. Support both online and offline mode.

**`alembic/versions/001_initial_schema.py`**: Auto-generated migration via `alembic revision --autogenerate`. Capture all 13 tables.

**Acceptance**: `alembic upgrade head` on a fresh PostgreSQL DB creates all tables without error.

---

## Wave 2 · Data Generation & Feature Engineering
> Depends on Wave 1 (models). Tasks 2.1 and 2.2 can run in parallel.

### Task 2.1 · `simulation/generator.py` — Synthetic Event Generator
**File**: `simulation/generator.py`

**Key class**:
```python
class SyntheticDataGenerator:
    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.fake = Faker(locale="en_IN")
        self.fake.seed_instance(seed)

    def generate(self, n_events: int = 20000) -> GeneratedDataset:
        """Returns GeneratedDataset with customers, events, profiles."""

    def _generate_segment_a(self, n: int) -> list[EventRecord]: ...
    def _generate_segment_b(self, n: int) -> list[EventRecord]: ...
    def _generate_segment_c(self, n: int) -> list[EventRecord]: ...
    def _generate_segment_d(self, n: int) -> list[EventRecord]: ...
    def _generate_segment_e(self, n: int) -> list[EventRecord]: ...
```

**`EventRecord` dataclass**:
```python
@dataclass
class EventRecord:
    event_id: str           # UUID string
    customer_id: str
    merchant_id: str
    segment: str            # A/B/C/D/E
    transaction_amount_paise: int
    payment_method: str     # upi/card/netbanking/wallet
    failure_code: str
    failure_category: str
    customer_ltv_paise: int
    previous_successes: int
    previous_failures: int
    subscription_age_days: int
    days_since_last_payment: float
    historical_payment_hour: int  # 0-23 (peak hour for this customer)
    historical_payment_day: int   # 0-6
    timestamp: datetime
    # Pre-computed per-channel success rates (from generated history)
    retry_success_rate: float
    whatsapp_success_rate: float
    email_success_rate: float
    upi_switch_success_rate: float
```

**Segment parameters** (implement exactly):

| Segment | N (of 20k) | Amount (paise) | LTV (paise) | Failure codes | Peak hour |
|---------|-----------|----------------|-------------|---------------|-----------|
| A | 5,000 | 50,000–1,500,000 | 2,000,000–8,000,000 | INSUFFICIENT_FUNDS (80%), CARD_DECLINED (20%) | 19–21 |
| B | 4,000 | 100,000–2,000,000 | 1,500,000–6,000,000 | UPI_FAILURE (70%), NETWORK_ERROR (30%) | random |
| C | 4,000 | 20,000–800,000 | 500,000–3,000,000 | AUTHENTICATION_FAILED (50%), CHECKOUT_ABANDONED (50%) | random |
| D | 3,000 | 500,000–5,000,000 | 10,000,000+ | CARD_DECLINED (40%), FRAUD_SUSPECTED (30%), AUTH_FAILED (30%) | random |
| E | 4,000 | 5,000–50,000 | 0–300,000 | INSUFFICIENT_FUNDS (50%), CARD_DECLINED (30%), UPI_FAILURE (20%) | random |

**Output**: Save to `simulation/data/events_{n}.json` (array of EventRecord as dicts) + `simulation/data/customers_{n}.json`.

**Performance**: Must complete in < 10 seconds for n=20,000.

**Acceptance**: `python -c "from simulation.generator import SyntheticDataGenerator; g = SyntheticDataGenerator(); d = g.generate(100); print(len(d.events))"` prints 100.

---

### Task 2.2 · `simulation/features.py` — Feature Engineering
**File**: `simulation/features.py`

**Function**:
```python
def build_feature_vector(event: EventRecord) -> dict:
    """
    Returns a dict of features ready for ML. All categoricals label-encoded.
    """
    return {
        "transaction_amount_paise": event.transaction_amount_paise,
        "payment_method_encoded": PAYMENT_METHOD_MAP[event.payment_method],
        "failure_code_encoded": FAILURE_CODE_MAP[event.failure_code],
        "customer_ltv_paise": event.customer_ltv_paise,
        "previous_successes": event.previous_successes,
        "previous_failures": event.previous_failures,
        "time_since_last_payment_days": event.days_since_last_payment,
        "historical_payment_hour": event.historical_payment_hour,
        "historical_payment_day": event.historical_payment_day,
        "retry_success_rate": event.retry_success_rate,
        "whatsapp_success_rate": event.whatsapp_success_rate,
        "upi_switch_success_rate": event.upi_switch_success_rate,
        "segment_encoded": SEGMENT_MAP[event.segment],
    }

def build_feature_dataframe(events: list[EventRecord]) -> pd.DataFrame:
    """Returns pandas DataFrame, one row per event."""
```

**Encoding maps** (define as module-level constants):
```python
PAYMENT_METHOD_MAP = {"upi": 0, "card": 1, "netbanking": 2, "wallet": 3}
FAILURE_CODE_MAP = {
    "INSUFFICIENT_FUNDS": 0, "CARD_DECLINED": 1, "UPI_FAILURE": 2,
    "NETWORK_ERROR": 3, "AUTHENTICATION_FAILED": 4, "CHECKOUT_ABANDONED": 5,
    "FRAUD_SUSPECTED": 6
}
SEGMENT_MAP = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}
```

**Acceptance**: `build_feature_dataframe(events)` returns DataFrame with 13 columns, no NaN values.

---

## Wave 3 · Simulation Engines
> Depends on Wave 2 (generator). Tasks 3.1 and 3.2 can run in parallel.

### Task 3.1 · `simulation/baseline_simulator.py`
**File**: `simulation/baseline_simulator.py`

**Logic**: For every event, attempt ONE immediate retry. Flat 15.4% recovery rate. Skip if `customer_ltv_paise < 300000 AND transaction_amount_paise < 50000` (Segment E proxy). No WAIT, no strategy selection, no policy.

**Costs**:
- Every retry costs 200 paise (₹2)
- No discounts

**Class**:
```python
class BaselineSimulator:
    RECOVERY_RATE = 0.154
    RETRY_COST_PAISE = 200
    LTV_SKIP_THRESHOLD_PAISE = 300_000
    AMOUNT_SKIP_THRESHOLD_PAISE = 50_000

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    def run(self, events: list[EventRecord]) -> SimulationResult:
        """
        Returns SimulationResult with:
        - total_events
        - total_revenue_at_risk_paise
        - total_recovered_paise
        - recovery_rate (float)
        - total_interventions
        - total_discount_cost_paise (always 0 for baseline)
        - total_recovery_cost_paise
        - net_recovered_paise
        - strategy_breakdown: dict (for baseline, just {"RETRY": {...}})
        """
```

**Target output** (for 10,000 events): recovery_rate ≈ 0.154, net_recovered ≈ ₹6.2L.

**Acceptance**: `BaselineSimulator().run(events)` returns dict with all required keys. recovery_rate ≈ 0.14–0.17.

---

### Task 3.2 · `simulation/razor_simulator.py`
**File**: `simulation/razor_simulator.py`

**Strategy selection rules** (deterministic lookup, in priority order):

```python
def select_strategy(event: EventRecord, current_hour: int) -> RecoveryStrategy:
    if event.segment == "E":
        return RecoveryStrategy.STOP
    if event.segment == "D" and event.transaction_amount_paise > 500_000:
        return RecoveryStrategy.HUMAN_ESCALATION
    if event.segment == "A":
        if current_hour in range(19, 22):  # 19, 20, 21
            return RecoveryStrategy.RETRY
        else:
            return RecoveryStrategy.WAIT  # wait until 20:00
    if event.segment == "B":
        return RecoveryStrategy.PAYMENT_METHOD_SWITCH
    if event.segment == "C":
        return RecoveryStrategy.WHATSAPP_REMINDER
    return RecoveryStrategy.RETRY  # default
```

**Recovery probabilities** (stochastic outcome draw):
```python
RECOVERY_PROBS = {
    ("A", "RETRY", True):   0.78,   # True = in_window
    ("A", "RETRY", False):  0.32,
    ("A", "WAIT",  None):   0.78,   # WAIT always resolves in-window
    ("B", "PAYMENT_METHOD_SWITCH", None): 0.81,
    ("B", "RETRY", None):   0.40,
    ("C", "WHATSAPP_REMINDER", None): 0.67,
    ("C", "EMAIL_REMINDER", None):    0.35,
    ("D", "HUMAN_ESCALATION", None):  0.85,
    ("D", "RETRY", None):   0.05,
    ("E", None, None):      0.05,   # catch-all for segment E
    ("default", None, None): 0.40,
}
```

**Strategy costs** (paise):
```python
STRATEGY_COSTS_PAISE = {
    "RETRY": 200,
    "PAYMENT_METHOD_SWITCH": 300,
    "WHATSAPP_REMINDER": 100,
    "EMAIL_REMINDER": 50,
    "PAYMENT_LINK": 0,
    "DISCOUNT_OFFER": None,  # computed: min(amount * 0.10, 100_000)
    "HUMAN_ESCALATION": 25_000,
    "WAIT": 0,
    "STOP": 0,
}
```

**Basic policy check** (Phase 1 version — full policy engine in Phase 3):
```python
def _policy_check(event: EventRecord, strategy: RecoveryStrategy) -> bool:
    # Block automated action on amounts > ₹50,000 (unless human escalation)
    if (event.transaction_amount_paise > 5_000_000
            and strategy != RecoveryStrategy.HUMAN_ESCALATION):
        return False  # blocked
    return True
```

**Class**:
```python
class RazorSimulator:
    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    def run(self, events: list[EventRecord], current_hour: int = 14) -> SimulationResult:
        """
        current_hour: simulated time of day (14 = 2PM default, tests WAIT behavior)
        Returns SimulationResult same shape as BaselineSimulator.run()
        + strategy_breakdown: dict[strategy_name, {attempts, recoveries, revenue_recovered_paise, cost_paise}]
        """
```

**Target output** (for 10,000 events, seed=42, current_hour=14):
- recovery_rate ≈ 0.27–0.30
- net_recovered ≈ ₹12L–₹14L
- STOP count ≈ 1,500–1,800 (Segment E)
- WAIT count ≈ 700–1,000 (Segment A out-of-window)
- PAYMENT_METHOD_SWITCH count ≈ 1,100–1,500

**Acceptance**:
- `RazorSimulator().run(events)` completes in < 5s for 10,000 events
- recovery_rate > BaselineSimulator().run(events).recovery_rate
- "STOP" in strategy_breakdown and "WAIT" in strategy_breakdown

---

## Wave 4 · Evaluator & CLI
> Depends on Wave 3. Tasks 4.1 and 4.2 can run in parallel.

### Task 4.1 · `simulation/evaluator.py` + `simulate.py`
**Files**: `simulation/evaluator.py`, `simulate.py`

**`simulation/evaluator.py`**:
```python
@dataclass
class SimulationResult:
    total_events: int
    total_revenue_at_risk_paise: int
    total_recovered_paise: int
    recovery_rate: float
    total_interventions: int
    total_discount_cost_paise: int
    total_recovery_cost_paise: int
    net_recovered_paise: int
    strategy_breakdown: dict[str, dict]  # per strategy stats

def format_inr(paise: int) -> str:
    """Format paise as ₹X.XL (lakhs) or ₹X,XXX for smaller amounts."""
    rupees = paise / 100
    if rupees >= 100_000:
        return f"₹{rupees/100_000:.2f}L"
    return f"₹{rupees:,.0f}"

def print_comparison_table(baseline: SimulationResult, razor: SimulationResult) -> None:
    """Prints rich-formatted comparison table to terminal."""

def print_strategy_breakdown(razor: SimulationResult) -> None:
    """Prints per-strategy breakdown table."""

def save_results(baseline: SimulationResult, razor: SimulationResult, path: str) -> None:
    """Saves both results to JSON."""
```

**`simulate.py`** (root-level CLI):
```python
#!/usr/bin/env python3
"""
RAZOR Revenue Recovery Simulator
Usage: python simulate.py [--events N] [--seed S] [--hour H]
"""
import argparse
from simulation.generator import SyntheticDataGenerator
from simulation.baseline_simulator import BaselineSimulator
from simulation.razor_simulator import RazorSimulator
from simulation.evaluator import print_comparison_table, print_strategy_breakdown, save_results

def main():
    parser = argparse.ArgumentParser(description="RAZOR Revenue Recovery Simulator")
    parser.add_argument("--events", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--hour", type=int, default=14,
                        help="Simulated current hour (0-23). Use 20 to see in-window RETRY behavior.")
    args = parser.parse_args()

    print(f"[RAZOR] Generating {args.events:,} events (seed={args.seed})...")
    dataset = SyntheticDataGenerator(seed=args.seed).generate(args.events)

    print("[RAZOR] Running baseline simulation...")
    baseline = BaselineSimulator(seed=args.seed).run(dataset.events)

    print(f"[RAZOR] Running RAZOR simulation (simulated hour: {args.hour}:00)...")
    razor = RazorSimulator(seed=args.seed).run(dataset.events, current_hour=args.hour)

    print_comparison_table(baseline, razor)
    print_strategy_breakdown(razor)
    save_results(baseline, razor, "simulation/data/results_latest.json")
    print("\n[RAZOR] Results saved to simulation/data/results_latest.json")

if __name__ == "__main__":
    main()
```

**Expected terminal output** (approximate, seed=42, 10k events, hour=14):
```
╔══════════════════════════════════════════════════════════╗
║            RAZOR SIMULATION RESULTS                      ║
╠══════════════════════════════════════╦═══════════╦═══════╣
║ Metric                               ║  Baseline ║ RAZOR ║
╠══════════════════════════════════════╬═══════════╬═══════╣
║ Revenue at risk                      ║  ₹48.XL   ║ ₹48.XL║
║ Revenue recovered                    ║   ₹7.XL   ║ ₹13.XL║
║ Recovery rate                        ║   15.4%   ║ ~28%  ║
║ Total interventions                  ║   X,XXX   ║ X,XXX ║
║ Discount cost                        ║   ₹X.XL   ║ ₹X.XL ║
║ Net revenue recovered                ║   ₹6.XL   ║ ₹12+L ║
╠══════════════════════════════════════╬═══════════╬═══════╣
║ INCREMENTAL REVENUE                  ║           ║ +₹X.XL║
╚══════════════════════════════════════╩═══════════╩═══════╝
```

**Acceptance**:
- `python simulate.py` runs end-to-end without error
- RAZOR recovery_rate > baseline recovery_rate
- RAZOR net_recovered_paise > baseline net_recovered_paise
- "STOP" and "WAIT" appear in strategy breakdown
- `simulation/data/results_latest.json` is created

---

### Task 4.2 · `scripts/seed_db.py`
**File**: `scripts/seed_db.py`

**Logic**:
1. Generate dataset with `SyntheticDataGenerator(seed=42).generate(20_000)`
2. Create one `Merchant` record (`id="merchant_001"`, name="Demo Merchant")
3. Bulk-insert all customers (use `INSERT ... ON CONFLICT DO NOTHING` for idempotency)
4. Bulk-insert all payments
5. Bulk-insert `CustomerRecoveryProfile` for each customer
6. Create default `Policy` for the merchant
7. Print counts of rows inserted

**Key implementation note**: Use SQLAlchemy Core `insert(...).on_conflict_do_nothing()` for idempotency.

**Acceptance**:
- `python scripts/seed_db.py` runs without error
- Re-running produces 0 new inserts (no duplicates)
- `SELECT COUNT(*) FROM customers` returns ~2,000+ distinct customers

---

### Task 4.3 · `README.md`
**File**: `README.md`

Minimal but complete. Include:
1. Project name + tagline: _"AI decides. ML predicts. Rules protect. APIs execute. Data proves."_
2. Architecture diagram (text art from PROJECT.md)
3. **Quick Start** section:
   ```bash
   # 1. Install dependencies
   pip install -e .

   # 2. Set up environment
   cp .env.example .env
   # Edit .env with your DATABASE_URL

   # 3. Run DB migrations
   alembic upgrade head

   # 4. Run the simulation
   python simulate.py

   # 5. (Optional) Seed the database
   python scripts/seed_db.py
   ```
4. Expected output description ("RAZOR recovers ~2x vs baseline")

---

## Verification Steps

Run these in order on a fresh checkout:

```bash
# Step 1: Install
pip install -e .

# Step 2: Check models import
python -c "from db.models import Merchant, RecoveryCase, Policy, RecoveryStrategy; print('✓ Models OK')"

# Step 3: Run migration (needs PostgreSQL running)
alembic upgrade head

# Step 4: Run simulation (no DB needed)
python simulate.py --events 10000 --seed 42 --hour 14

# Expected: RAZOR recovery rate > 15%, STOP and WAIT appear in breakdown

# Step 5: Run with in-window hour (should increase Segment A recovery)
python simulate.py --events 1000 --seed 42 --hour 20

# Step 6: Seed DB (needs PostgreSQL)
python scripts/seed_db.py

# Step 7: Verify idempotency
python scripts/seed_db.py  # should print 0 new rows
```

---

## Files Created / Modified

| File | Type | Purpose |
|------|------|---------|
| `pyproject.toml` | NEW | Project deps & config |
| `requirements.txt` | NEW | pip-installable deps |
| `.env.example` | NEW | Environment template |
| `README.md` | NEW | Project docs + quick start |
| `config.py` | NEW | Pydantic settings |
| `db/__init__.py` | NEW | Package init |
| `db/base.py` | NEW | SQLAlchemy Base |
| `db/database.py` | NEW | Engine + session |
| `db/models.py` | NEW | All 13 ORM models + enums |
| `alembic.ini` | NEW | Alembic config |
| `alembic/env.py` | NEW | Migration env |
| `alembic/versions/001_initial_schema.py` | NEW | Initial migration |
| `simulation/__init__.py` | NEW | Package init |
| `simulation/generator.py` | NEW | Synthetic data generator |
| `simulation/features.py` | NEW | Feature engineering |
| `simulation/baseline_simulator.py` | NEW | Baseline simulator |
| `simulation/razor_simulator.py` | NEW | RAZOR rule-based simulator |
| `simulation/evaluator.py` | NEW | Metrics + formatting |
| `simulate.py` | NEW | CLI entry point |
| `scripts/__init__.py` | NEW | Package init |
| `scripts/seed_db.py` | NEW | DB seeding script |

---

## Phase Acceptance Criteria

| ID | Criteria | How to verify |
|----|----------|---------------|
| PA-1.1 | `python simulate.py` runs without errors | Run it |
| PA-1.2 | RAZOR recovery_rate > baseline (target: ~28% vs ~15%) | Check output table |
| PA-1.3 | RAZOR net_recovered > baseline net_recovered | Check output table |
| PA-1.4 | WAIT + STOP + PAYMENT_METHOD_SWITCH all appear in strategy breakdown | Check breakdown table |
| PA-1.5 | `python -c "from db.models import *"` imports cleanly | Run it |
| PA-1.6 | `alembic upgrade head` creates all 13 tables | Check DB schema |
| PA-1.7 | `python scripts/seed_db.py` is idempotent | Run twice, count rows |
| PA-1.8 | `simulation/data/events_20000.json` exists after generator run | Check file |
| PA-1.9 | All amounts in DB and simulation are integer paise (no floats) | Code review |
