import logging
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import Connection

from review_removal_tracker.data_collection.places_client import PlacesClient
from review_removal_tracker.db.crud.businesses import deactivate_business, get_active_businesses
from review_removal_tracker.db.crud.snapshots import (
    get_latest_snapshot,
    get_snapshots_for_window,
    upsert_snapshot,
)
from review_removal_tracker.db.models import DailySnapshot

logger = logging.getLogger(__name__)


@dataclass
class SnapshotJobResult:
    total: int = 0
    fetched: int = 0
    skipped: int = 0
    deactivated: int = 0
    errors: int = 0


def run_snapshot_job(
    conn: Connection,
    client: PlacesClient,
    snapshot_date: date | None = None,
    skip_inactive_days: int = 14,
) -> SnapshotJobResult:
    today = snapshot_date or date.today()
    businesses = get_active_businesses(conn)
    result = SnapshotJobResult(total=len(businesses))

    for business in businesses:
        if business.id is None:
            continue

        try:
            if _should_skip(conn, business.id, today, skip_inactive_days):
                logger.debug("Skipping inactive business %s", business.place_id)
                result.skipped += 1
                continue

            details = client.get_place_details(business.place_id)

            if details is None:
                logger.info("Business %s not found on Google, deactivating", business.place_id)
                deactivate_business(conn, business.place_id)
                result.deactivated += 1
                continue

            upsert_snapshot(conn, DailySnapshot(
                business_id=business.id,
                snapshot_date=today,
                review_count=details.review_count,
                rating=details.rating,
            ))
            result.fetched += 1

        except Exception:
            logger.exception("Error processing business %s", business.place_id)
            result.errors += 1

    return result


def _should_skip(conn: Connection, business_id: int, today: date, skip_inactive_days: int) -> bool:
    latest = get_latest_snapshot(conn, business_id)
    # Never skip a business we haven't collected data for yet.
    if latest is None:
        return False

    days_since_latest = (today - latest.snapshot_date).days
    # Never skip within the normal daily polling window — only consider skipping
    # if the last snapshot is already skip_inactive_days or more days old.
    if days_since_latest < skip_inactive_days:
        return False

    window = get_snapshots_for_window(conn, business_id, today, skip_inactive_days)
    # Need at least two data points to compare oldest vs. newest review count.
    if len(window) < 2:
        return False

    # Skip only if the review count is completely flat across the window —
    # no reviews added or removed means the business is inactive.
    # TODO: once skipped, a business stays skipped indefinitely since its latest snapshot
    # date never advances. Add a periodic re-check (e.g. weekly) to catch businesses
    # that become active again after a long quiet period.
    return window[0].review_count == window[-1].review_count
