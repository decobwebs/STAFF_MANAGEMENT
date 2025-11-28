"""add conversation_id to messages

Revision ID: 5732602edc86
Revises: 57f49c2c13a4
Create Date: 2025-11-27 23:25:26.576973

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5732602edc86'
down_revision: Union[str, None] = '57f49c2c13a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    # Step 1: Add column as nullable first
    op.add_column('messages', sa.Column('conversation_id', sa.Integer(), nullable=True))
    
    # Step 2: Create foreign key (optional at this stage)
    op.create_foreign_key('fk_messages_conversation', 'messages', 'conversations', ['conversation_id'], ['id'])
    


def downgrade() -> None:
    pass
