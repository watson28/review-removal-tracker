"""Seed the businesses table by running Text Search across a city's
discovery categories x districts.

Usage:
    uv run python scripts/run_discovery.py [--city PATH] [--dry-run]

City-specific values (categories, districts, name) come from a TOML
file — defaults to config/cities/berlin.toml. See grid/city.py for the
schema. Discovery queries are formed as "{category} in {district}, {city}".
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from review_removal_tracker.config import get_settings
from review_removal_tracker.data_collection.discovery_job import run_discovery_job
from review_removal_tracker.data_collection.places_client import PlacesClient
from review_removal_tracker.db.engine import get_connection
from review_removal_tracker.grid.city import load_city_config
from review_removal_tracker.telemetry import init_metrics, shutdown_metrics

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CITY_CONFIG = PROJECT_ROOT / "config" / "cities" / "berlin.toml"


def build_queries(categories: tuple[str, ...], districts: tuple[str, ...]) -> list[tuple[str, str]]:
    return [(c, d) for d in districts for c in categories]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--city",
        default=str(DEFAULT_CITY_CONFIG),
        help=f"Path to city config TOML (default: {DEFAULT_CITY_CONFIG})",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print queries without calling the API or DB")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    city = load_city_config(args.city)
    if not city.discovery_categories or not city.discovery_districts:
        logger.error(
            "City config %s has empty discovery.categories or discovery.districts",
            args.city,
        )
        return 1

    queries = build_queries(city.discovery_categories, city.discovery_districts)
    logger.info(
        "Built %d discovery queries for %s (%d categories x %d districts)",
        len(queries), city.name, len(city.discovery_categories), len(city.discovery_districts),
    )

    if args.dry_run:
        for cat, dist in queries:
            print(f"  {cat} in {dist}, {city.name}")
        return 0

    settings = get_settings()

    meter = init_metrics("rrt-discovery", endpoint=settings.otel_exporter_endpoint)
    queries_counter = meter.create_counter("rrt.discovery.total_queries")
    upserted_counter = meter.create_counter("rrt.discovery.upserted")
    errors_counter = meter.create_counter("rrt.discovery.errors")
    duration_gauge = meter.create_gauge("rrt.discovery.duration_seconds")
    if not settings.google_api_key:
        logger.error("GOOGLE_API_KEY is not set — cannot run discovery")
        return 1

    client = PlacesClient(api_key=settings.google_api_key)

    start = time.monotonic()
    with get_connection() as conn:
        result = run_discovery_job(conn, client, queries, city_name=city.name)
    elapsed = time.monotonic() - start

    queries_counter.add(result.total_queries)
    upserted_counter.add(result.upserted)
    errors_counter.add(result.errors)
    duration_gauge.set(elapsed)

    logger.info(
        "Discovery done for %s: %d queries, %d upserted, %d errors (%.1fs)",
        city.name, result.total_queries, result.upserted, result.errors, elapsed,
    )

    shutdown_metrics()
    return 0 if result.errors == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
