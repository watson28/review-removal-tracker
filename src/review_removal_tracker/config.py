import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Settings:
    database_url: str
    db_pool_size: int = 3
    db_max_overflow: int = 2
    google_api_key: str | None = None
    discovery_queries: list[tuple[str, str]] = field(default_factory=list)
    skip_inactive_days: int = 14


def get_settings() -> Settings:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")

    google_api_key = os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        logger.warning("GOOGLE_API_KEY is not set — data collection will not work")

    discovery_queries = _parse_discovery_queries(os.environ.get("DISCOVERY_QUERIES", ""))

    return Settings(
        database_url=database_url,
        db_pool_size=int(os.environ.get("DB_POOL_SIZE", "3")),
        db_max_overflow=int(os.environ.get("DB_MAX_OVERFLOW", "2")),
        google_api_key=google_api_key,
        discovery_queries=discovery_queries,
        skip_inactive_days=int(os.environ.get("SKIP_INACTIVE_DAYS", "14")),
    )


def _parse_discovery_queries(raw: str) -> list[tuple[str, str]]:
    if not raw:
        return []
    queries = []
    for pair in raw.split(";"):
        pair = pair.strip()
        if not pair:
            continue
        parts = pair.split(":", 1)
        if len(parts) == 2:
            queries.append((parts[0].strip(), parts[1].strip()))
    return queries
