"""add_ticket_indexes

Revision ID: b1c2d3e4f5a6
Revises: f3a4b5c6d7e8
Create Date: 2026-06-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = 'f3a4b5c6d7e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Índice composto para o filtro+ordem mais comum: WHERE status=? ORDER BY created_at DESC
    op.create_index('ix_tickets_status_created_at', 'tickets', ['status', 'created_at'])
    # Índices para os filtros de progresso e prioridade
    op.create_index('ix_tickets_progress', 'tickets', ['progress'])
    op.create_index('ix_tickets_priority', 'tickets', ['priority'])


def downgrade() -> None:
    op.drop_index('ix_tickets_priority', table_name='tickets')
    op.drop_index('ix_tickets_progress', table_name='tickets')
    op.drop_index('ix_tickets_status_created_at', table_name='tickets')
