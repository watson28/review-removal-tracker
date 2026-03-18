import os
from dataclasses import dataclass


@dataclass
class Settings:
    database_url: str
    db_pool_size: int = 3
    db_max_overflow: int = 2


def get_settings() -> Settings:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return Settings(
        database_url=database_url,
        db_pool_size=int(os.environ.get("DB_POOL_SIZE", "3")),
        db_max_overflow=int(os.environ.get("DB_MAX_OVERFLOW", "2")),
    )
