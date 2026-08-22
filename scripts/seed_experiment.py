"""Seed a demo A/B experiment (control vs treatment arms) if none exists."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import SessionLocal
from db.models import Experiment
from engine.experiment_engine import ExperimentEngine

DEMO_EXPERIMENT = "Recovery Strategy A/B"
ARMS = [
    {"arm_name": "control", "traffic_percent": 40, "strategy": None},
    {"arm_name": "retry", "traffic_percent": 20, "strategy": "RETRY"},
    {"arm_name": "whatsapp", "traffic_percent": 20, "strategy": "WHATSAPP_REMINDER"},
    {"arm_name": "upi_switch", "traffic_percent": 20, "strategy": "PAYMENT_METHOD_SWITCH"},
]


def main() -> int:
    engine = ExperimentEngine()
    session = SessionLocal()
    try:
        existing = session.query(Experiment).filter_by(name=DEMO_EXPERIMENT).first()
        if existing is not None:
            print(f"Experiment '{DEMO_EXPERIMENT}' already exists; skipping.")
            return 0
        experiment = engine.create_experiment(session, DEMO_EXPERIMENT, ARMS, "merchant_001")
        print(f"Created experiment '{experiment.name}' id={experiment.id} with {len(experiment.arms)} arms.")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
