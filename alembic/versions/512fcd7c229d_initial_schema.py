"""initial schema

Revision ID: 512fcd7c229d
Revises: 
Create Date: 2025-11-25 22:27:26.688271

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '512fcd7c229d'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns as nullable first (to avoid NOT NULL violation)
    op.add_column('daily_reports', sa.Column('achievements', sa.Text(), nullable=True))
    op.add_column('daily_reports', sa.Column('challenges', sa.Text(), nullable=True))
    op.add_column('daily_reports', sa.Column('completed_tasks', sa.Text(), nullable=True))
    op.add_column('daily_reports', sa.Column('plans_for_tomorrow', sa.Text(), nullable=True))
    
    # Optionally: set empty string as default for existing rows
    op.execute("UPDATE daily_reports SET achievements = '', challenges = '', completed_tasks = '', plans_for_tomorrow = ''")
    
    # Now alter columns to be NOT NULL (since all rows have values)
    op.alter_column('daily_reports', 'achievements', nullable=False, server_default='')
    op.alter_column('daily_reports', 'challenges', nullable=False, server_default='')
    op.alter_column('daily_reports', 'completed_tasks', nullable=False, server_default='')
    op.alter_column('daily_reports', 'plans_for_tomorrow', nullable=False, server_default='')
    
    # Finally, drop the old 'content' column
    op.drop_column('daily_reports', 'content')


def downgrade() -> None:
    # Re-add 'content' column
    op.add_column('daily_reports', sa.Column('content', sa.Text(), nullable=False, server_default=''))
    
    # Drop the structured columns
    op.drop_column('daily_reports', 'plans_for_tomorrow')
    op.drop_column('daily_reports', 'completed_tasks')
    op.drop_column('daily_reports', 'challenges')
    op.drop_column('daily_reports', 'achievements')