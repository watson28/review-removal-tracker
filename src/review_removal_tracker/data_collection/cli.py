import logging

from review_removal_tracker.data_collection.discovery_job import run_discovery_job
from review_removal_tracker.data_collection.places_client import PlacesClient
from review_removal_tracker.data_collection.snapshot_job import run_snapshot_job
from review_removal_tracker.config import get_settings
from review_removal_tracker.db.engine import get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def run_snapshot() -> None:
    settings = get_settings()
    client = PlacesClient(api_key=settings.google_api_key or "")
    with get_connection() as conn:
        result = run_snapshot_job(conn, client, skip_inactive_days=settings.skip_inactive_days)
    print(f"Snapshot done: {result}")


def run_discovery() -> None:
    settings = get_settings()
    client = PlacesClient(api_key=settings.google_api_key or "")
    with get_connection() as conn:
        result = run_discovery_job(conn, client, settings.discovery_queries)
    print(f"Discovery done: {result}")
