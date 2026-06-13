"""add_mural

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-06-13 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e2f3a4b5c6d7'
down_revision: Union[str, Sequence[str], None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # mural_posts
    op.create_table(
        "mural_posts",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_mural_posts_created_at", "mural_posts", ["created_at"])

    # mural_comments
    op.create_table(
        "mural_comments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("mural_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_mural_comments_post_id", "mural_comments", ["post_id"])

    # mural_acks
    op.create_table(
        "mural_acks",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("mural_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.UniqueConstraint("post_id", "user_id", name="uq_mural_ack"),
    )

    # Add mural_post_id to notifications
    op.add_column(
        "notifications",
        sa.Column("mural_post_id", sa.Integer(), sa.ForeignKey("mural_posts.id", ondelete="SET NULL"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("notifications", "mural_post_id")
    op.drop_table("mural_acks")
    op.drop_table("mural_comments")
    op.drop_table("mural_posts")
