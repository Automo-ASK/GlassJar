"""collection custom fields + payment form responses

Revision ID: 4a4a59a84eb8
Revises: 44c0d8fa9ff6
Create Date: 2026-07-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a4a59a84eb8'
down_revision: Union[str, None] = '44c0d8fa9ff6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('collections', sa.Column('custom_fields', sa.JSON(), nullable=True))
    op.add_column('payments', sa.Column('form_responses', sa.JSON(), nullable=True))
    op.add_column(
        'payments',
        sa.Column('form_submitted_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('payments', 'form_submitted_at')
    op.drop_column('payments', 'form_responses')
    op.drop_column('collections', 'custom_fields')
