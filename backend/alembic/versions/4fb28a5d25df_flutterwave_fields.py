"""add flutterwave fields to payments and expenses

Revision ID: 4fb28a5d25df
Revises: 76b1c92dbcce
Create Date: 2026-07-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4fb28a5d25df'
down_revision: Union[str, None] = '76b1c92dbcce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('payments', sa.Column('flw_customer_id', sa.String(length=64), nullable=True))
    op.add_column('payments', sa.Column('flw_virtual_account_id', sa.String(length=64), nullable=True))
    op.add_column('payments', sa.Column('va_account_number', sa.String(length=32), nullable=True))
    op.add_column('payments', sa.Column('va_bank_name', sa.String(length=128), nullable=True))
    op.add_column('payments', sa.Column('va_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('expenses', sa.Column('flw_transfer_id', sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column('expenses', 'flw_transfer_id')
    op.drop_column('payments', 'va_expires_at')
    op.drop_column('payments', 'va_bank_name')
    op.drop_column('payments', 'va_account_number')
    op.drop_column('payments', 'flw_virtual_account_id')
    op.drop_column('payments', 'flw_customer_id')
