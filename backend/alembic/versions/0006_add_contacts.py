"""add contact_info to user_profiles

Revision ID: 0006_add_contact_info
Revises: 0005_team_requests_tbl
Create Date: 2025-01-28 03:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '0006_add_contact_info'
down_revision = '0005_team_requests_tbl'
branch_labels = None
depends_on = None

def column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    insp = inspect(bind)
    columns = [c['name'] for c in insp.get_columns(table_name)]
    return column_name in columns

def upgrade() -> None:
    if not column_exists('user_profiles', 'contact_info'):
        op.add_column(
            'user_profiles',
            sa.Column('contact_info', sa.String(length=300), nullable=True)
        )

def downgrade() -> None:
    if column_exists('user_profiles', 'contact_info'):
        op.drop_column('user_profiles', 'contact_info')