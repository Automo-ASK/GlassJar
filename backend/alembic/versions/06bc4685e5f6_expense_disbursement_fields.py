"""add expense disbursement fields (bank code, raw payload, manual flag)

Revision ID: 06bc4685e5f6
Revises: 4bd1ca6c4cc0
Create Date: 2026-07-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '06bc4685e5f6'
down_revision: Union[str, None] = '4bd1ca6c4cc0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('expenses', sa.Column('destination_bank_code', sa.String(length=16), nullable=True))
    op.add_column('expenses', sa.Column('raw_payout_payload', sa.JSON(), nullable=True))
    op.add_column(
        'expenses',
        sa.Column('manual_payout', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column('expenses', 'manual_payout')
    op.drop_column('expenses', 'raw_payout_payload')
    op.drop_column('expenses', 'destination_bank_code')
