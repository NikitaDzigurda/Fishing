"""add scholar identifiers, metrics to user_profiles and create articles table

Revision ID: 0004_add_scholar_metrics
Revises: 0003_add_profile_fields
Create Date: 2025-01-28 01:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0004_add_scholar_metrics'  # 👈 Короткое имя (22 символа)
down_revision = '0003_add_profile_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # === Добавляем идентификаторы научных баз в user_profiles ===
    op.add_column(
        'user_profiles',
        sa.Column('google_scholar_id', sa.String(length=100), nullable=True)
    )
    op.add_column(
        'user_profiles',
        sa.Column('scopus_id', sa.String(length=100), nullable=True)
    )
    op.add_column(
        'user_profiles',
        sa.Column('orcid', sa.String(length=50), nullable=True)
    )
    op.add_column(
        'user_profiles',
        sa.Column('arxiv_name', sa.String(length=200), nullable=True)
    )
    op.add_column(
        'user_profiles',
        sa.Column('semantic_scholar_id', sa.String(length=100), nullable=True)
    )

    # === Добавляем метрики автора в user_profiles ===
    op.add_column(
        'user_profiles',
        sa.Column('citations_total', sa.Integer(), nullable=True, server_default='0')
    )
    op.add_column(
        'user_profiles',
        sa.Column('citations_recent', sa.Integer(), nullable=True, server_default='0')
    )
    op.add_column(
        'user_profiles',
        sa.Column('h_index', sa.Integer(), nullable=True, server_default='0')
    )
    op.add_column(
        'user_profiles',
        sa.Column('i10_index', sa.Integer(), nullable=True, server_default='0')
    )
    op.add_column(
        'user_profiles',
        sa.Column('publication_count', sa.Integer(), nullable=True, server_default='0')
    )
    op.add_column(
        'user_profiles',
        sa.Column('metrics_updated_at', sa.DateTime(timezone=True), nullable=True)
    )

    # === Создаём таблицу articles ===
    op.create_table(
        'articles',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('title', sa.String(length=1000), nullable=False),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('abstract', sa.Text(), nullable=True),
        sa.Column('doi', sa.String(length=255), nullable=True),
        sa.Column('arxiv_id', sa.String(length=100), nullable=True),
        sa.Column('url', sa.String(length=500), nullable=True),
        sa.Column('venue', sa.String(length=500), nullable=True),
        sa.Column('citations', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('author_user_ids', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('authors_list', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('external_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index('ix_articles_id', 'articles', ['id'], unique=False)
    op.create_index('ix_articles_title', 'articles', ['title'], unique=False)
    op.create_index('ix_articles_year', 'articles', ['year'], unique=False)
    op.create_index('ix_articles_doi', 'articles', ['doi'], unique=True)
    op.create_index('ix_articles_arxiv_id', 'articles', ['arxiv_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_articles_arxiv_id', table_name='articles')
    op.drop_index('ix_articles_doi', table_name='articles')
    op.drop_index('ix_articles_year', table_name='articles')
    op.drop_index('ix_articles_title', table_name='articles')
    op.drop_index('ix_articles_id', table_name='articles')
    op.drop_table('articles')

    op.drop_column('user_profiles', 'metrics_updated_at')
    op.drop_column('user_profiles', 'publication_count')
    op.drop_column('user_profiles', 'i10_index')
    op.drop_column('user_profiles', 'h_index')
    op.drop_column('user_profiles', 'citations_recent')
    op.drop_column('user_profiles', 'citations_total')
    op.drop_column('user_profiles', 'semantic_scholar_id')
    op.drop_column('user_profiles', 'arxiv_name')
    op.drop_column('user_profiles', 'orcid')
    op.drop_column('user_profiles', 'scopus_id')
    op.drop_column('user_profiles', 'google_scholar_id')