"""FastAPI dependency injection configuration."""

from typing import Generator

from sqlmodel import Session as DBSession
from sqlmodel import create_engine

from config import load_config
from repositories import SessionRepository

_config = load_config()
_engine = create_engine(_config.database.url)


def get_db_session() -> Generator[DBSession, None, None]:
    """Yields a database session, ensuring proper cleanup."""
    with DBSession(_engine) as session:
        yield session


def get_session_repository(
    db_session: DBSession,
) -> SessionRepository:
    """Creates a SessionRepository with the provided database session."""
    return SessionRepository(db_session)
