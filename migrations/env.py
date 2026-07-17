"""Alembic environment — configured for Resume Optimizer."""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.paths import DB_PATH
from app.database.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_url() -> str:
    """Return the sqlalchemy URL, falling back to the default DB_PATH."""
    return config.get_main_option("sqlalchemy.url") or f"sqlite:///{DB_PATH}"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — generate SQL without connecting."""
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against the live database."""
    current_config = context.config
    url = current_config.get_main_option("sqlalchemy.url") or f"sqlite:///{DB_PATH}"
    current_config.set_main_option("sqlalchemy.url", url)

    connectable = engine_from_config(
        current_config.get_section(current_config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
