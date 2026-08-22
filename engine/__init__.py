"""RAZOR decision engine — strategy selection, policy enforcement, state machine.

Wave 1 delivers the deterministic recovery state machine and the strategy
engine (expected-net-recovery with WAIT/STOP) with direct PostgreSQL logging.
Wave 2 adds the policy hard gate and simulator-backed outcome verifier.
"""
