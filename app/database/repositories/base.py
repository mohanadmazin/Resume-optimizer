"""Base repository with common database operations."""
from abc import ABC

from sqlalchemy.orm import Session


class BaseRepository(ABC):
    """Abstract base class for all repositories."""

    def __init__(self, session: Session):
        self.session = session

    def add(self, obj) -> None:
        """Add an object to the session."""
        self.session.add(obj)

    def flush(self) -> None:
        """Flush changes without committing."""
        self.session.flush()
