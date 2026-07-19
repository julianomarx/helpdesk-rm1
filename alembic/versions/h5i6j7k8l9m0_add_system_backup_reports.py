"""add system_backup_reports

Revision ID: h5i6j7k8l9m0
Revises: g4h5i6j7k8l9
Create Date: 2026-07-16

"""
from alembic import op
import sqlalchemy as sa

revision = 'h5i6j7k8l9m0'
down_revision = 'g4h5i6j7k8l9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'system_backup_reports',
        sa.Column('id',           sa.Integer(),    primary_key=True, autoincrement=True),
        sa.Column('report_date',  sa.Date(),        nullable=False),
        sa.Column('report_time',  sa.String(10),    nullable=True),
        sa.Column('status',       sa.String(10),    nullable=False),
        sa.Column('errors_count', sa.Integer(),     server_default='0'),
        sa.Column('total_size',   sa.String(20),    nullable=True),
        sa.Column('disk_free',    sa.String(20),    nullable=True),
        sa.Column('report_lines', sa.Text(),        nullable=True),
        sa.Column('received_at',  sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_backup_reports_date', 'system_backup_reports', ['report_date'])


def downgrade():
    op.drop_index('ix_backup_reports_date', 'system_backup_reports')
    op.drop_table('system_backup_reports')
