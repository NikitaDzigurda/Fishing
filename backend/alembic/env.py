import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy import engine_from_config

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ensure project root is on path so imports like `backend.models` work
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# import metadata from app models for 'autogenerate'
try:
    from backend.database import Base
    import backend.models  # noqa: F401 - ensure model classes are imported

    target_metadata = Base.metadata
except Exception:
    target_metadata = None


def get_url():
    # Use DATABASE_URL from environment if present; alembic/SQLAlchemy expects a sync driver
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@db:5432/authorityprompt",
    )
    # remove async driver suffix for alembic (sync engine)
    return url.replace("+asyncpg", "")


def run_migrations_online():
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    raise RuntimeError("alembic offline mode is not configured in this template")
else:
    run_migrations_online()
