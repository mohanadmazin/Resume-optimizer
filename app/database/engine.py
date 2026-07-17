"""Database engine and configuration."""

import logging
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

from app.core.paths import DB_PATH

logger = logging.getLogger(__name__)


def create_sqlite_engine(path: Path = DB_PATH) -> Engine:
    """Create a SQLite engine with PRAGMAs for production use.

    Enables foreign keys, WAL mode, busy timeout, and normal synchronous
    mode on every new connection.
    """
    engine = create_engine(
        f"sqlite:///{path}",
        echo=False,
        pool_pre_ping=True,
        connect_args={
            "timeout": 5.0,
            "check_same_thread": False,
        },
    )

    @event.listens_for(engine, "connect")
    def configure_sqlite(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
        finally:
            cursor.close()

    return engine


engine = create_sqlite_engine()


def init_db() -> None:
    """Create all tables if they don't exist.

    Kept for isolated tests. Production startup should use run_migrations().
    """
    from app.database.models import Base
    logger.debug("Initializing database at %s", DB_PATH)
    Base.metadata.create_all(engine)
