import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Settings:
    database_url: str
    db_pool_size: int = 3
    db_max_overflow: int = 2
    google_api_key: str | None = None
    otel_exporter_endpoint: str | None = None
    skip_inactive_days: int = 14


def get_settings() -> Settings:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")

    google_api_key = os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        logger.warning("GOOGLE_API_KEY is not set — data collection will not work")

    return Settings(
        database_url=database_url,
        db_pool_size=int(os.environ.get("DB_POOL_SIZE", "3")),
        db_max_overflow=int(os.environ.get("DB_MAX_OVERFLOW", "2")),
        google_api_key=google_api_key,
        otel_exporter_endpoint=os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"),
        skip_inactive_days=int(os.environ.get("SKIP_INACTIVE_DAYS", "14")),
    )
