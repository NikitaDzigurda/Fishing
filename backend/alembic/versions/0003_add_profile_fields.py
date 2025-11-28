"""add bio, major, university to user_profiles

Revision ID: 0003_add_profile_fields
Revises: 0002_create_user_profiles_table
Create Date: 2025-01-28 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0003_add_profile_fields'
down_revision = '0002_create_user_profiles_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'user_profiles',
        sa.Column('bio', sa.Text(), nullable=True)
    )
    op.add_column(
        'user_profiles',
        sa.Column('major', sa.String(length=200), nullable=True)
    )
    op.add_column(
        'user_profiles',
        sa.Column('university', sa.String(length=300), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('user_profiles', 'university')
    op.drop_column('user_profiles', 'major')
    op.drop_column('user_profiles', 'bio')