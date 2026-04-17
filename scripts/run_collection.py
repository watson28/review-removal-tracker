"""Fetch a snapshot for every active business and write it to daily_snapshots.

Usage:
    uv run python scripts/run_collection.py

Reads GOOGLE_API_KEY, DATABASE_URL, and SKIP_INACTIVE_DAYS from the
environment (see review_removal_tracker.config).
"""
from __future__ import annotations

import logging
import sys
import time

from review_removal_tracker.config import get_settings
from review_removal_tracker.data_collection.places_client import PlacesClient
from review_removal_tracker.data_collection.snapshot_job import run_snapshot_job
from review_removal_tracker.db.engine import get_connection
from review_removal_tracker.telemetry import init_metrics, shutdown_metrics

logger = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    settings = get_settings()

    meter = init_metrics("rrt-collection", endpoint=settings.otel_exporter_endpoint)
    total_counter = meter.create_counter("rrt.collection.total")
    fetched_counter = meter.create_counter("rrt.collection.fetched")
    skipped_counter = meter.create_counter("rrt.collection.skipped")
    deactivated_counter = meter.create_counter("rrt.collection.deactivated")
    errors_counter = meter.create_counter("rrt.collection.errors")
    duration_gauge = meter.create_gauge("rrt.collection.duration_seconds")
    if not settings.google_api_key:
        logger.error("GOOGLE_API_KEY is not set — cannot run collection")
        return 1

    client = PlacesClient(api_key=settings.google_api_key)

    start = time.monotonic()
    with get_connection() as conn:
        result = run_snapshot_job(conn, client, skip_inactive_days=settings.skip_inactive_days)
    elapsed = time.monotonic() - start

    total_counter.add(result.total)
    fetched_counter.add(result.fetched)
    skipped_counter.add(result.skipped)
    deactivated_counter.add(result.deactivated)
    errors_counter.add(result.errors)
    duration_gauge.set(elapsed)

    logger.info(
        "Snapshot done: %d total, %d fetched, %d skipped, %d deactivated, %d errors (%.1fs)",
        result.total, result.fetched, result.skipped, result.deactivated, result.errors, elapsed,
    )

    shutdown_metrics()
    return 0 if result.errors == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
