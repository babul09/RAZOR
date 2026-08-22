"""Reproducible offline training CLI for the RAZOR recovery-prediction model.

Trains logistic and XGBoost candidates on a deterministic synthetic dataset,
selects the trusted model, and persists it as a versioned joblib artifact.

Usage:
    python scripts/train_recovery_model.py [--events 20000] [--seed 42] \\
        [--output ml/artifacts/recovery_model.joblib]

Fully offline — no PostgreSQL, Redis, Gemini, or payment integration required.
"""
from __future__ import annotations

import argparse
import os
import sys

# Ensure the project root is importable when invoked as
# ``python scripts/train_recovery_model.py`` (script dir is otherwise first
# on sys.path, hiding the top-level ``ml`` package).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Train and persist the RAZOR recovery-prediction model."
    )
    parser.add_argument(
        "--events", type=int, default=20_000,
        help="Number of synthetic events to generate (default: 20000).",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Deterministic seed for generation and training (default: 42).",
    )
    parser.add_argument(
        "--output", default="ml/artifacts/recovery_model.joblib",
        help="Output artifact path (default: ml/artifacts/recovery_model.joblib).",
    )
    args = parser.parse_args(argv)

    if args.events < 1:
        raise ValueError("--events must be a positive integer")

    # Deliberately import heavy/first-party modules here (not at module top) so
    # the CLI never touches DB/Redis/Gemini/payment modules.
    from ml.recovery_model import RecoveryModel
    from ml.training import compare_models
    from simulation.generator import SyntheticDataGenerator

    print(f"Generating {args.events} synthetic events (seed={args.seed})...")
    events = SyntheticDataGenerator(seed=args.seed).generate(args.events).events

    print("Comparing logistic vs XGBoost on the same holdout...")
    result = compare_models(events, seed=args.seed)

    selected = result["selected_model"]
    model = RecoveryModel(result["pipeline"])
    model.save(args.output, metrics=result)

    print()
    for name in ("logistic", "xgboost"):
        rec = result[name]
        print(
            f"  {name:<10} roc_auc={rec['roc_auc']:.4f}  "
            f"log_loss={rec['log_loss']:.4f}  brier={rec['brier']:.4f}"
        )
    print(f"  selected   : {selected}")
    print(f"  artifact   : {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
