"""RAZOR agent layer — LLM-assisted diagnosis and explanation (Phase 4).

Safe design constraint (NFR-05): these agents are read-only. They never execute
a payment, never run money arithmetic, and are never in the money/payment
critical path. Diagnosis is the informational front of the recovery pipeline.
"""
