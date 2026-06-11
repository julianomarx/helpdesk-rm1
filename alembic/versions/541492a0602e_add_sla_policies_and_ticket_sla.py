"""add_sla_policies_and_ticket_sla

Revision ID: 541492a0602e
Revises: a6314558201c
Create Date: 2026-06-11 09:08:23.894427

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


# revision identifiers, used by Alembic.
revision: str = '541492a0602e'
down_revision: Union[str, Sequence[str], None] = 'a6314558201c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Schema ────────────────────────────────────────────────────────────────
    op.create_table(
        'sla_policies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('first_response_hours', sa.Integer(), nullable=False),
        sa.Column('resolution_hours', sa.Integer(), nullable=False),
        sa.Column('priority', sa.Enum('low', 'medium', 'high', name='priorityenum', native_enum=False), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_table(
        'ticket_sla',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_id', sa.Integer(), nullable=False),
        sa.Column('policy_id', sa.Integer(), nullable=True),
        sa.Column('first_response_hours', sa.Integer(), nullable=False),
        sa.Column('resolution_hours', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('response_deadline', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolution_deadline', sa.DateTime(timezone=True), nullable=False),
        sa.Column('response_met_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_met_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paused_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_paused_seconds', sa.Integer(), nullable=False),
        sa.Column('response_breached', sa.Boolean(), nullable=False),
        sa.Column('resolution_breached', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['policy_id'], ['sla_policies.id']),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticket_id'),
    )
    op.add_column('subcategories', sa.Column('sla_policy_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'subcategories', 'sla_policies', ['sla_policy_id'], ['id'])

    # ── Seed: 5 políticas padrão ──────────────────────────────────────────────
    sla_policies_t = table(
        'sla_policies',
        column('id', sa.Integer),
        column('name', sa.String),
        column('description', sa.Text),
        column('first_response_hours', sa.Integer),
        column('resolution_hours', sa.Integer),
        column('priority', sa.String),
    )
    op.bulk_insert(sla_policies_t, [
        {'id': 1, 'name': 'Crítico',   'description': 'Impacto total na operação (chaves, rede crítica)',
         'first_response_hours': 1,  'resolution_hours': 4,   'priority': 'high'},
        {'id': 2, 'name': 'Urgente',   'description': 'Impacto significativo (fiscal, infraestrutura)',
         'first_response_hours': 2,  'resolution_hours': 8,   'priority': 'high'},
        {'id': 3, 'name': 'Normal',    'description': 'Chamados operacionais do dia a dia',
         'first_response_hours': 4,  'resolution_hours': 24,  'priority': 'medium'},
        {'id': 4, 'name': 'Baixo',     'description': 'Solicitações administrativas sem urgência',
         'first_response_hours': 8,  'resolution_hours': 72,  'priority': 'low'},
        {'id': 5, 'name': 'Planejado', 'description': 'Tarefas planejadas sem impacto imediato',
         'first_response_hours': 24, 'resolution_hours': 168, 'priority': 'low'},
    ])

    # ── Seed: atribuição das 26 subcategorias ─────────────────────────────────
    # Mapeamento: subcategory_id → sla_policy_id
    # 1=Crítico  2=Urgente  3=Normal  4=Baixo  5=Planejado
    subcategory_policy_map = {
        1: 3,   # Monitores e Periféricos
        2: 3,   # Usuários/Email
        3: 3,   # Impressoras e Scanners
        4: 2,   # Impressora Fiscal (TÉRMICA)   → Urgente
        5: 2,   # Rede e Internet               → Urgente
        6: 2,   # Infraestrutura                → Urgente
        7: 1,   # Sistema de Chaves Eletrônicas → Crítico
        8: 3,   # Sistema de Ponto
        9: 3,   # Outros (TI)
        10: 4,  # Relatórios                    → Baixo
        11: 3,  # Permissões
        12: 3,  # Problemas Gerais (PMS)
        13: 1,  # Chaves Magnetizadas pelo Opera → Crítico
        14: 4,  # Notas                          → Baixo
        15: 4,  # Boletos                        → Baixo
        16: 3,  # Outros (Fiscal)
        17: 5,  # Cadastro de Itens              → Planejado
        18: 3,  # Busca de Hóspedes
        19: 3,  # Impressão
        20: 3,  # Problemas Gerais (PDV)
        21: 3,  # Outros (PDV)
        22: 4,  # Novo usuário                   → Baixo
        23: 4,  # Inativar usuário               → Baixo
        24: 3,  # Substituição de usuário
        25: 3,  # Problemas de acesso/permissões
        26: 3,  # Outros (Usuários)
    }

    conn = op.get_bind()
    for sub_id, policy_id in subcategory_policy_map.items():
        conn.execute(
            sa.text("UPDATE subcategories SET sla_policy_id = :pid WHERE id = :sid"),
            {"pid": policy_id, "sid": sub_id},
        )


def downgrade() -> None:
    op.drop_constraint(None, 'subcategories', type_='foreignkey')
    op.drop_column('subcategories', 'sla_policy_id')
    op.drop_table('ticket_sla')
    op.drop_table('sla_policies')
