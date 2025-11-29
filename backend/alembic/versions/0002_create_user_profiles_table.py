"""create user_profiles table

Revision ID: 0002_create_user_profiles_table
Revises: 0001_create_users_table
Create Date: 2025-11-28 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002_create_user_profiles_table'
down_revision = '0001_create_users_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure sequence does not already exist (idempotency for environments with leftovers)
    op.execute("DROP SEQUENCE IF EXISTS user_profiles_id_seq CASCADE")
    op.create_table(
        'user_profiles',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('first_name', sa.String(length=150), nullable=True),
        sa.Column('last_name', sa.String(length=150), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_user_profiles_user_id'), 'user_profiles', ['user_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_profiles_user_id'), table_name='user_profiles')
    op.drop_table('user_profiles')
    # Drop the sequence if it still exists
    op.execute("DROP SEQUENCE IF EXISTS user_profiles_id_seq CASCADE")
