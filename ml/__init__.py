"""RAZOR ML layer — recovery prediction models.

This package exposes a deterministic, offline recovery-prediction API built on
Phase 1 synthetic events. It trains a logistic-regression baseline and (in
Plan 02) an XGBoost challenger, then exposes per-strategy recovery
probabilities through :class:`ml.recovery_model.RecoveryModel`.
"""
