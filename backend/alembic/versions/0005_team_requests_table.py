"""create team_requests table

Revision ID: 0005_team_requests_tbl
Revises: 0004_add_scholar_metrics
Create Date: 2025-01-28 02:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '0005_team_requests_tbl'  # Короткое имя (< 32 символов)
down_revision = '0004_add_scholar_metrics'
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    insp = inspect(bind)
    return table_name in insp.get_table_names()


def upgrade() -> None:
    if not table_exists('team_requests'):
        op.create_table(
            'team_requests',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('title', sa.String(length=200), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('required_roles', sa.JSON(), nullable=False, server_default='[]'),
            sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
            sa.Column('recommended_user_ids', sa.JSON(), nullable=True, server_default='[]'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),

            # Foreign Key
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        )

        op.create_index(
            op.f('ix_team_requests_id'),
            'team_requests',
            ['id'],
            unique=False
        )
        op.create_index(
            op.f('ix_team_requests_user_id'),
            'team_requests',
            ['user_id'],
            unique=False
        )


def downgrade() -> None:
    if table_exists('team_requests'):
        op.drop_index(op.f('ix_team_requests_user_id'), table_name='team_requests')
        op.drop_index(op.f('ix_team_requests_id'), table_name='team_requests')
        op.drop_table('team_requests')