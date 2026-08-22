"""
RAZOR — SQLAlchemy ORM Models

All monetary amounts stored as INTEGER PAISE (1 rupee = 100 paise).
NEVER use Float for money.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Float, ForeignKey,
    Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from db.base import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

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
    A = "A"  # Evening retry
    B = "B"  # UPI switch
    C = "C"  # WhatsApp reminder
    D = "D"  # Human escalation (high LTV)
    E = "E"  # Abandon (low LTV, cost > value)


class Merchant(Base):
    __tablename__ = "merchants"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    customers = relationship("Customer", back_populates="merchant")
    policies = relationship("Policy", back_populates="merchant", uselist=False)


class Customer(Base):
    __tablename__ = "customers"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    merchant_id = Column(String(36), ForeignKey("merchants.id"), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    lifetime_value_paise = Column(BigInteger, default=0, nullable=False)  # PAISE
    preferred_payment_method = Column(String(50), nullable=True)
    typical_payment_hour_start = Column(Integer, nullable=True)  # 0-23
    typical_payment_hour_end = Column(Integer, nullable=True)    # 0-23
    customer_segment = Column(String(1), nullable=True)  # A/B/C/D/E
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    merchant = relationship("Merchant", back_populates="customers")
    payments = relationship("Payment", back_populates="customer")
    recovery_cases = relationship("RecoveryCase", back_populates="customer")
    recovery_profile = relationship("CustomerRecoveryProfile", back_populates="customer", uselist=False)


class Payment(Base):
    __tablename__ = "payments"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    merchant_id = Column(String(36), ForeignKey("merchants.id"), nullable=False)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    amount_paise = Column(BigInteger, nullable=False)  # PAISE
    currency = Column(String(3), default="INR", nullable=False)
    payment_method = Column(String(50), nullable=True)
    status = Column(String(50), nullable=False)
    failure_code = Column(String(100), nullable=True)
    failure_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    customer = relationship("Customer", back_populates="payments")
    attempts = relationship("PaymentAttempt", back_populates="payment")


class PaymentAttempt(Base):
    __tablename__ = "payment_attempts"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    payment_id = Column(String(36), ForeignKey("payments.id"), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False)
    failure_code = Column(String(100), nullable=True)
    attempted_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    payment = relationship("Payment", back_populates="attempts")


class RecoveryCase(Base):
    __tablename__ = "recovery_cases"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    merchant_id = Column(String(36), ForeignKey("merchants.id"), nullable=False)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    source_type = Column(String(50), nullable=True)  # e.g. "payment"
    source_id = Column(String(36), nullable=True)    # FK to source record
    amount_at_risk_paise = Column(BigInteger, nullable=False)  # PAISE
    failure_code = Column(String(100), nullable=True)
    failure_reason = Column(Text, nullable=True)
    recovery_probability = Column(Float, nullable=True)
    expected_recovery_value_paise = Column(BigInteger, nullable=True)  # PAISE
    status = Column(String(50), default=RecoveryCaseStatus.NEW.value, nullable=False)
    priority = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    customer = relationship("Customer", back_populates="recovery_cases")
    actions = relationship("RecoveryAction", back_populates="case")
    decisions = relationship("AgentDecision", back_populates="case")
    outcomes = relationship("RecoveryOutcome", back_populates="case")
    audit_logs = relationship("AuditLog", back_populates="case")


class CustomerRecoveryProfile(Base):
    __tablename__ = "customer_recovery_profiles"
    __table_args__ = (UniqueConstraint("customer_id"),)
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    merchant_id = Column(String(36), ForeignKey("merchants.id"), nullable=False)
    retry_attempts = Column(Integer, default=0)
    retry_successes = Column(Integer, default=0)
    whatsapp_attempts = Column(Integer, default=0)
    whatsapp_successes = Column(Integer, default=0)
    email_attempts = Column(Integer, default=0)
    email_successes = Column(Integer, default=0)
    upi_switch_attempts = Column(Integer, default=0)
    upi_switch_successes = Column(Integer, default=0)
    discount_attempts = Column(Integer, default=0)
    discount_successes = Column(Integer, default=0)
    overall_recovery_probability = Column(Float, default=0.5)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="recovery_profile")


class RecoveryAction(Base):
    __tablename__ = "recovery_actions"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("recovery_cases.id"), nullable=False)
    strategy = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="PENDING")
    cost_paise = Column(BigInteger, default=0)  # PAISE
    executed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    outcome = Column(String(50), nullable=True)

    case = relationship("RecoveryCase", back_populates="actions")
    outcomes = relationship("RecoveryOutcome", back_populates="action")


class AgentDecision(Base):
    __tablename__ = "agent_decisions"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("recovery_cases.id"), nullable=False)
    input_json = Column(JSONB, nullable=True)
    strategies_evaluated_json = Column(JSONB, nullable=True)
    selected_strategy = Column(String(50), nullable=True)
    reasoning = Column(Text, nullable=True)
    policy_check_passed = Column(Boolean, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    case = relationship("RecoveryCase", back_populates="decisions")


class RecoveryOutcome(Base):
    __tablename__ = "recovery_outcomes"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("recovery_cases.id"), nullable=False)
    action_id = Column(String(36), ForeignKey("recovery_actions.id"), nullable=True)
    revenue_recovered_paise = Column(BigInteger, default=0)  # PAISE
    cost_of_recovery_paise = Column(BigInteger, default=0)   # PAISE
    net_revenue_recovered_paise = Column(BigInteger, default=0)  # PAISE
    recovery_method = Column(String(50), nullable=True)
    recovered_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    case = relationship("RecoveryCase", back_populates="outcomes")
    action = relationship("RecoveryAction", back_populates="outcomes")


class Experiment(Base):
    __tablename__ = "experiments"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    merchant_id = Column(String(36), ForeignKey("merchants.id"), nullable=False)
    name = Column(String(255), nullable=False)
    status = Column(String(50), default="ACTIVE")
    config_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    arms = relationship("ExperimentArm", back_populates="experiment")


class ExperimentArm(Base):
    __tablename__ = "experiment_arms"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    experiment_id = Column(String(36), ForeignKey("experiments.id"), nullable=False)
    arm_name = Column(String(100), nullable=False)
    traffic_percent = Column(Float, nullable=False)
    strategy = Column(String(50), nullable=True)
    attempts = Column(Integer, default=0)
    recoveries = Column(Integer, default=0)
    revenue_recovered_paise = Column(BigInteger, default=0)  # PAISE

    experiment = relationship("Experiment", back_populates="arms")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("recovery_cases.id"), nullable=True)
    event_type = Column(String(100), nullable=False)
    details_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    case = relationship("RecoveryCase", back_populates="audit_logs")


class Policy(Base):
    __tablename__ = "policies"
    __table_args__ = (UniqueConstraint("merchant_id"),)
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    merchant_id = Column(String(36), ForeignKey("merchants.id"), nullable=False)
    max_discount_percent = Column(Integer, default=10)
    max_automated_amount_paise = Column(BigInteger, default=500_000)  # ₹5,000 PAISE
    max_contacts_count = Column(Integer, default=3)
    max_contacts_window_days = Column(Integer, default=7)
    require_human_approval_above_paise = Column(BigInteger, default=500_000)  # ₹5,000 PAISE
    allowed_channels = Column(JSONB, default=lambda: ["whatsapp", "email"])
    stop_if_payment_succeeds = Column(Boolean, default=True)

    merchant = relationship("Merchant", back_populates="policies")
