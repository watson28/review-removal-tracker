"""Fetch a snapshot for every active business and write it to daily_snapshots.

Usage:
    uv run python scripts/run_collection.py

Reads GOOGLE_API_KEY, DATABASE_URL, and SKIP_INACTIVE_DAYS from the
environment (see review_removal_tracker.config).
"""
from __future__ import annotations

import logging
import sys

from review_removal_tracker.config import get_settings
from review_removal_tracker.data_collection.places_client import PlacesClient
from review_removal_tracker.data_collection.snapshot_job import run_snapshot_job
from review_removal_tracker.db.engine import get_connection

logger = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    settings = get_settings()
    if not settings.google_api_key:
        logger.error("GOOGLE_API_KEY is not set — cannot run collection")
        return 1

    client = PlacesClient(api_key=settings.google_api_key)
    with get_connection() as conn:
        result = run_snapshot_job(conn, client, skip_inactive_days=settings.skip_inactive_days)

    logger.info(
        "Snapshot done: %d total, %d fetched, %d skipped, %d deactivated, %d errors",
        result.total, result.fetched, result.skipped, result.deactivated, result.errors,
    )
    return 0 if result.errors == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
