from datetime import date
from decimal import Decimal

from review_removal_tracker.db.crud.businesses import upsert_business
from review_removal_tracker.db.crud.snapshots import (
    get_latest_snapshot,
    get_snapshots_for_window,
    upsert_snapshot,
    upsert_snapshots_bulk,
)
from review_removal_tracker.db.models import Business, DailySnapshot


def make_business(conn, place_id="ChIJ_snap_test") -> int:
    b = upsert_business(
        conn,
        Business(
            place_id=place_id,
            name="Snap Test",
            category="restaurant",
            district="Mitte",
            lat=Decimal("52.52"),
            lng=Decimal("13.40"),
        ),
    )
    return b.id


def test_upsert_snapshot_inserts(conn):
    bid = make_business(conn)
    snap = upsert_snapshot(conn, DailySnapshot(
        business_id=bid,
        snapshot_date=date(2026, 1, 1),
        review_count=100,
        rating=Decimal("4.2"),
    ))
    assert snap.id is not None
    assert snap.review_count == 100


def test_upsert_snapshot_is_idempotent(conn):
    bid = make_business(conn, "idempotent_snap")
    d = date(2026, 1, 1)
    upsert_snapshot(conn, DailySnapshot(bid, d, 100, Decimal("4.2")))
    snap = upsert_snapshot(conn, DailySnapshot(bid, d, 110, Decimal("4.3")))
    assert snap.review_count == 110
    assert snap.rating == Decimal("4.3")


def test_get_snapshots_for_window(conn):
    bid = make_business(conn, "window_snap")
    for day in range(1, 35):
        upsert_snapshot(conn, DailySnapshot(
            business_id=bid,
            snapshot_date=date(2026, 1, day) if day <= 31 else date(2026, 2, day - 31),
            review_count=100 + day,
            rating=Decimal("4.0"),
        ))

    snaps = get_snapshots_for_window(conn, bid, date(2026, 1, 31), 30)
    assert len(snaps) == 30
    assert all(s.snapshot_date <= date(2026, 1, 31) for s in snaps)


def test_get_latest_snapshot(conn):
    bid = make_business(conn, "latest_snap")
    upsert_snapshot(conn, DailySnapshot(bid, date(2026, 1, 1), 100, Decimal("4.0")))
    upsert_snapshot(conn, DailySnapshot(bid, date(2026, 1, 5), 120, Decimal("4.1")))
    upsert_snapshot(conn, DailySnapshot(bid, date(2026, 1, 3), 110, Decimal("4.05")))

    latest = get_latest_snapshot(conn, bid)
    assert latest.snapshot_date == date(2026, 1, 5)
    assert latest.review_count == 120


def test_get_latest_snapshot_none(conn):
    bid = make_business(conn, "no_snaps")
    assert get_latest_snapshot(conn, bid) is None


def test_upsert_snapshots_bulk(conn):
    bid = make_business(conn, "bulk_snap")
    snaps = [
        DailySnapshot(bid, date(2026, 1, i), 100 + i, Decimal("4.0"))
        for i in range(1, 6)
    ]
    count = upsert_snapshots_bulk(conn, snaps)
    assert count == 5
