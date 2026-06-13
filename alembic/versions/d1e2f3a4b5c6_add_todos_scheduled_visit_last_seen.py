"""add_todos_scheduled_visit_last_seen

Revision ID: d1e2f3a4b5c6
Revises: c7e8f9a1b2d3
Create Date: 2026-06-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = 'c7e8f9a1b2d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # last_seen_at on users
    op.add_column('users', sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True))

    # scheduled_visit_at on tickets
    op.add_column('tickets', sa.Column('scheduled_visit_at', sa.DateTime(timezone=True), nullable=True))

    # todos table
    op.create_table(
        'todos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('creator_id', sa.Integer(), nullable=False),
        sa.Column('assignee_id', sa.Integer(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('done', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('done_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['creator_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assignee_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_todos_assignee_id', 'todos', ['assignee_id'])
    op.create_index('ix_todos_creator_id', 'todos', ['creator_id'])
    op.create_index('ix_todos_done', 'todos', ['done'])


def downgrade() -> None:
    op.drop_index('ix_todos_done', table_name='todos')
    op.drop_index('ix_todos_creator_id', table_name='todos')
    op.drop_index('ix_todos_assignee_id', table_name='todos')
    op.drop_table('todos')
    op.drop_column('tickets', 'scheduled_visit_at')
    op.drop_column('users', 'last_seen_at')
