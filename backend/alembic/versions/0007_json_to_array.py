"""change articles columns from JSON to ARRAY

Revision ID: 0007_json_to_array
Revises: 0006_add_contact_info
Create Date: 2025-01-28 04:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0007_json_to_array'
down_revision = '0006_add_contact_info'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Удаляем старые колонки типа JSON
    op.drop_column('articles', 'author_user_ids')
    op.drop_column('articles', 'authors_list')

    # 2. Создаем новые колонки типа ARRAY
    op.add_column(
        'articles',
        sa.Column('author_user_ids', postgresql.ARRAY(sa.Integer()), nullable=False, server_default='{}')
    )
    op.add_column(
        'articles',
        sa.Column('authors_list', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}')
    )


def downgrade() -> None:
    # Обратный процесс: удаляем ARRAY, создаем JSON
    op.drop_column('articles', 'authors_list')
    op.drop_column('articles', 'author_user_ids')

    op.add_column(
        'articles',
        sa.Column('author_user_ids', sa.JSON(), server_default='[]', nullable=False)
    )
    op.add_column(
        'articles',
        sa.Column('authors_list', sa.JSON(), server_default='[]', nullable=False)
    )