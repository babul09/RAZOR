# RAZOR

> AI decides. ML predicts. Rules protect. APIs execute. Data proves.

RAZOR is a closed-loop revenue recovery simulator for failed payments. It compares a simple retry baseline with a policy-aware strategy engine using deterministic synthetic Indian payment data.

## Architecture

```text
Ingest → Risk Engine → Diagnosis Agent → Recovery Predictor
→ Strategy Engine → Policy / Guardrail → Auto Action or Human Review
→ Outcome Verifier → Learning / Analytics
```

## Quick Start

```bash
pip install -e .
cp .env.example .env
# Edit .env with your DATABASE_URL
alembic upgrade head
python simulate.py
python scripts/seed_db.py
```

The simulation writes JSON data and results under `simulation/data/`, and prints a comparison of revenue at risk, recovered revenue, recovery cost, and net recovery. RAZOR is designed to recover roughly twice the baseline revenue in the demo scenario.