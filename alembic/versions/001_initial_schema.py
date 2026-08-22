"""initial schema

Revision ID: 001
Revises: 
Create Date: 2026-08-22 11:23:16.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. merchants
    op.create_table('merchants',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. customers
    op.create_table('customers',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('merchant_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('lifetime_value_paise', sa.BigInteger(), nullable=False),
        sa.Column('preferred_payment_method', sa.String(length=50), nullable=True),
        sa.Column('typical_payment_hour_start', sa.Integer(), nullable=True),
        sa.Column('typical_payment_hour_end', sa.Integer(), nullable=True),
        sa.Column('customer_segment', sa.String(length=1), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. payments
    op.create_table('payments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('merchant_id', sa.String(length=36), nullable=False),
        sa.Column('customer_id', sa.String(length=36), nullable=False),
        sa.Column('amount_paise', sa.BigInteger(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('payment_method', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('failure_code', sa.String(length=100), nullable=True),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. payment_attempts
    op.create_table('payment_attempts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('payment_id', sa.String(length=36), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('failure_code', sa.String(length=100), nullable=True),
        sa.Column('attempted_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 5. recovery_cases
    op.create_table('recovery_cases',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('merchant_id', sa.String(length=36), nullable=False),
        sa.Column('customer_id', sa.String(length=36), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=True),
        sa.Column('source_id', sa.String(length=36), nullable=True),
        sa.Column('amount_at_risk_paise', sa.BigInteger(), nullable=False),
        sa.Column('failure_code', sa.String(length=100), nullable=True),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('recovery_probability', sa.Float(), nullable=True),
        sa.Column('expected_recovery_value_paise', sa.BigInteger(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 6. customer_recovery_profiles
    op.create_table('customer_recovery_profiles',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('customer_id', sa.String(length=36), nullable=False),
        sa.Column('merchant_id', sa.String(length=36), nullable=False),
        sa.Column('retry_attempts', sa.Integer(), nullable=True),
        sa.Column('retry_successes', sa.Integer(), nullable=True),
        sa.Column('whatsapp_attempts', sa.Integer(), nullable=True),
        sa.Column('whatsapp_successes', sa.Integer(), nullable=True),
        sa.Column('email_attempts', sa.Integer(), nullable=True),
        sa.Column('email_successes', sa.Integer(), nullable=True),
        sa.Column('upi_switch_attempts', sa.Integer(), nullable=True),
        sa.Column('upi_switch_successes', sa.Integer(), nullable=True),
        sa.Column('discount_attempts', sa.Integer(), nullable=True),
        sa.Column('discount_successes', sa.Integer(), nullable=True),
        sa.Column('overall_recovery_probability', sa.Float(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('customer_id')
    )

    # 7. recovery_actions
    op.create_table('recovery_actions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('case_id', sa.String(length=36), nullable=False),
        sa.Column('strategy', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('cost_paise', sa.BigInteger(), nullable=True),
        sa.Column('executed_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('outcome', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['recovery_cases.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 8. agent_decisions
    op.create_table('agent_decisions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('case_id', sa.String(length=36), nullable=False),
        sa.Column('input_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('strategies_evaluated_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('selected_strategy', sa.String(length=50), nullable=True),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('policy_check_passed', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['recovery_cases.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 9. recovery_outcomes
    op.create_table('recovery_outcomes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('case_id', sa.String(length=36), nullable=False),
        sa.Column('action_id', sa.String(length=36), nullable=True),
        sa.Column('revenue_recovered_paise', sa.BigInteger(), nullable=True),
        sa.Column('cost_of_recovery_paise', sa.BigInteger(), nullable=True),
        sa.Column('net_revenue_recovered_paise', sa.BigInteger(), nullable=True),
        sa.Column('recovery_method', sa.String(length=50), nullable=True),
        sa.Column('recovered_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['action_id'], ['recovery_actions.id'], ),
        sa.ForeignKeyConstraint(['case_id'], ['recovery_cases.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 10. experiments
    op.create_table('experiments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('merchant_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('config_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 11. experiment_arms
    op.create_table('experiment_arms',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('experiment_id', sa.String(length=36), nullable=False),
        sa.Column('arm_name', sa.String(length=100), nullable=False),
        sa.Column('traffic_percent', sa.Float(), nullable=False),
        sa.Column('strategy', sa.String(length=50), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=True),
        sa.Column('recoveries', sa.Integer(), nullable=True),
        sa.Column('revenue_recovered_paise', sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(['experiment_id'], ['experiments.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 12. audit_logs
    op.create_table('audit_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('case_id', sa.String(length=36), nullable=True),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('details_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['recovery_cases.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 13. policies
    op.create_table('policies',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('merchant_id', sa.String(length=36), nullable=False),
        sa.Column('max_discount_percent', sa.Integer(), nullable=True),
        sa.Column('max_automated_amount_paise', sa.BigInteger(), nullable=True),
        sa.Column('max_contacts_count', sa.Integer(), nullable=True),
        sa.Column('max_contacts_window_days', sa.Integer(), nullable=True),
        sa.Column('require_human_approval_above_paise', sa.BigInteger(), nullable=True),
        sa.Column('allowed_channels', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('stop_if_payment_succeeds', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('merchant_id')
    )


def downgrade() -> None:
    op.drop_table('policies')
    op.drop_table('audit_logs')
    op.drop_table('experiment_arms')
    op.drop_table('experiments')
    op.drop_table('recovery_outcomes')
    op.drop_table('agent_decisions')
    op.drop_table('recovery_actions')
    op.drop_table('customer_recovery_profiles')
    op.drop_table('recovery_cases')
    op.drop_table('payment_attempts')
    op.drop_table('payments')
    op.drop_table('customers')
    op.drop_table('merchants')
