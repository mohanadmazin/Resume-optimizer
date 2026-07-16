"""Database engine and initialization."""
import logging

from sqlalchemy import create_engine

from app.core.paths import DB_PATH

logger = logging.getLogger(__name__)

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)


def init_db() -> None:
    """Create all tables if they don't exist."""
    from app.database.models import Base
    logger.debug("Initializing database at %s", DB_PATH)
    Base.metadata.create_all(engine)
