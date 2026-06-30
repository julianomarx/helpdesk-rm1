"""add_performance_indexes

Revision ID: g4h5i6j7k8l9
Revises: b1c2d3e4f5a6
Create Date: 2026-06-30 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op


revision: str = 'g4h5i6j7k8l9'
down_revision: Union[str, Sequence[str], None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # tickets.updated_at — usado em queries de chamados parados (updated_at < NOW() - X)
    op.create_index('ix_tickets_updated_at', 'tickets', ['updated_at'])

    # ticket_logs.action + created_at — dashboard de histórico e produtividade
    op.create_index('ix_ticket_logs_action_created_at', 'ticket_logs', ['action', 'created_at'])

    # ticket_comments.ticket_id — subquery NOT EXISTS em chamados parados
    op.create_index('ix_ticket_comments_ticket_id_created_at', 'ticket_comments', ['ticket_id', 'created_at'])

    # ticket_sla — queries de SLA violado por equipe/política
    op.create_index('ix_ticket_sla_resolution_breached', 'ticket_sla', ['resolution_breached'])


def downgrade() -> None:
    op.drop_index('ix_ticket_sla_resolution_breached', table_name='ticket_sla')
    op.drop_index('ix_ticket_comments_ticket_id_created_at', table_name='ticket_comments')
    op.drop_index('ix_ticket_logs_action_created_at', table_name='ticket_logs')
    op.drop_index('ix_tickets_updated_at', table_name='tickets')
