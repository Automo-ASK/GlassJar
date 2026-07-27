"""make payment entry_id/member_id nullable for anonymous public payments

Revision ID: 4bd1ca6c4cc0
Revises: 4a4a59a84eb8
Create Date: 2026-07-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4bd1ca6c4cc0'
down_revision: Union[str, None] = '4a4a59a84eb8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('payments') as batch_op:
        batch_op.alter_column('entry_id', existing_type=sa.Integer(), nullable=True)
        batch_op.alter_column('member_id', existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table('payments') as batch_op:
        batch_op.alter_column('member_id', existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column('entry_id', existing_type=sa.Integer(), nullable=False)
