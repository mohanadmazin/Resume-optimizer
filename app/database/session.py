"""Database session management."""
from contextlib import contextmanager

from sqlalchemy.orm import sessionmaker

from app.database.engine import engine

SessionLocal = sessionmaker(bind=engine)


@contextmanager
def get_session():
    """Provide a transactional session scope."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
