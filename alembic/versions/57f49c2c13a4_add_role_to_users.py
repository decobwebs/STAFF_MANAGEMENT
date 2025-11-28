"""add role to users

Revision ID: 57f49c2c13a4
Revises: 512fcd7c229d
Create Date: 2025-11-27 13:57:22.746525

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '57f49c2c13a4'
down_revision: Union[str, None] = '512fcd7c229d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('users', sa.Column('role', sa.String(), nullable=True, server_default='staff'))

def downgrade():
    op.drop_column('users', sa.Column('role'))