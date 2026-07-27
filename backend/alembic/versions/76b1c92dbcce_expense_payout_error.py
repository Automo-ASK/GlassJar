"""add expense payout_error column

Revision ID: 76b1c92dbcce
Revises: 06bc4685e5f6
Create Date: 2026-07-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '76b1c92dbcce'
down_revision: Union[str, None] = '06bc4685e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('expenses', sa.Column('payout_error', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('expenses', 'payout_error')
