"""add va_amount to payments

Revision ID: 686796f35aed
Revises: 4fb28a5d25df
Create Date: 2026-07-29 22:45:48.565180

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '686796f35aed'
down_revision: Union[str, None] = '4fb28a5d25df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("va_amount", sa.Numeric(12, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("payments", "va_amount")
