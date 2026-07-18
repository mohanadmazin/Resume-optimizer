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
    database_engine = create_engine(
        f"sqlite:///{path}",
        echo=False,
        pool_pre_ping=True,
        connect_args={
            "timeout": 5.0,
            "check_same_thread": False,
        },
    )

    @event.listens_for(database_engine, "connect")
    def configure_sqlite(dbapi_connection, _connection_record) -> None:
        previous_autocommit = getattr(
            dbapi_connection,
            "autocommit",
            None,
        )

        try:
            if previous_autocommit is not None:
                dbapi_connection.autocommit = True

            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA busy_timeout=5000")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
            finally:
                cursor.close()
        finally:
            if previous_autocommit is not None:
                dbapi_connection.autocommit = previous_autocommit

    return database_engine


engine = create_sqlite_engine()
