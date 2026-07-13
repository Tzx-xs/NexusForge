"""Alembic environment configuration for Xingyuanbi.

Uses native sqlite3 data access layer (not SQLAlchemy ORM); Alembic only manages DDL migration scripts.
The runtime database URL is retrieved from Container.database.db_path via environment variable.
"""

import os
import sys
from logging.config import fileConfig

# Ensure project root is in sys.path so migration scripts can import project modules
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import create_engine, pool

from alembic import context

# Alembic Config object
config = context.config

# Logging configuration
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url from environment variable or default path
# Container sets XINGYUANBI_DB_PATH during initialization
db_path = os.environ.get("XINGYUANBI_DB_PATH", os.path.join(backend_dir, "data", "xingyuanbi.db"))
db_url = f"sqlite:///{db_path}"

# Ensure data directory exists
os.makedirs(os.path.dirname(db_path), exist_ok=True)

# Override sqlalchemy.url in alembic.ini
config.set_main_option("sqlalchemy.url", db_url)

# Create SQLAlchemy Engine (used only by Alembic migrations; runtime uses native sqlite3)
connectable = create_engine(db_url, poolclass=pool.NullPool)


def run_migrations_offline() -> None:
    """Offline mode: generate SQL scripts without connecting to the database."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=None,  # No ORM MetaData used
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Online mode: connect to the database and run migrations."""
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=None,  # No ORM MetaData used
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
