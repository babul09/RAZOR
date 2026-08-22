"""recovery_memory table (FR-11 learning loop)

Revision ID: 002
Revises: 001
Create Date: 2026-08-22 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'recovery_memory',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('customer_id', sa.String(length=36), nullable=False),
        sa.Column('failure_type', sa.String(length=100), nullable=True),
        sa.Column('strategy', sa.String(length=50), nullable=False),
        sa.Column('outcome', sa.String(length=50), nullable=False),
        sa.Column('recovered', sa.Boolean(), nullable=False),
        sa.Column('amount_paise', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_recovery_memory_customer_id', 'recovery_memory', ['customer_id'])


def downgrade() -> None:
    op.drop_index('ix_recovery_memory_customer_id', table_name='recovery_memory')
    op.drop_table('recovery_memory')
