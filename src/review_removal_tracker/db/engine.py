from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, Connection, Engine

from review_removal_tracker.config import get_settings

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_pre_ping=True,
        )
    return _engine


@contextmanager
def get_connection() -> Generator[Connection, None, None]:
    with get_engine().begin() as conn:
        yield conn


@contextmanager
def get_raw_connection() -> Generator[Connection, None, None]:
    """Yields a connection without auto-commit — caller manages transaction."""
    with get_engine().connect() as conn:
        yield conn
