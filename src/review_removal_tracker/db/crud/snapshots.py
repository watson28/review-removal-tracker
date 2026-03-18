from datetime import date, timedelta

from sqlalchemy import Connection, select
from sqlalchemy.dialects.postgresql import insert

from review_removal_tracker.db import schema
from review_removal_tracker.db.models import DailySnapshot


def _row_to_snapshot(row) -> DailySnapshot:
    return DailySnapshot(
        id=row.id,
        business_id=row.business_id,
        snapshot_date=row.snapshot_date,
        review_count=row.review_count,
        rating=row.rating,
    )


def upsert_snapshot(conn: Connection, snapshot: DailySnapshot) -> DailySnapshot:
    stmt = (
        insert(schema.daily_snapshots)
        .values(
            business_id=snapshot.business_id,
            snapshot_date=snapshot.snapshot_date,
            review_count=snapshot.review_count,
            rating=snapshot.rating,
        )
        .on_conflict_do_update(
            constraint="uq_snapshots_business_date",
            set_={
                "review_count": snapshot.review_count,
                "rating": snapshot.rating,
            },
        )
        .returning(schema.daily_snapshots)
    )
    row = conn.execute(stmt).mappings().one()
    return _row_to_snapshot(row)


def upsert_snapshots_bulk(conn: Connection, snapshots: list[DailySnapshot]) -> int:
    if not snapshots:
        return 0
    count = 0
    for snapshot in snapshots:
        upsert_snapshot(conn, snapshot)
        count += 1
    return count


def get_snapshots_for_window(
    conn: Connection, business_id: int, end_date: date, window_days: int
) -> list[DailySnapshot]:
    start_date = end_date - timedelta(days=window_days)
    stmt = (
        select(schema.daily_snapshots)
        .where(
            schema.daily_snapshots.c.business_id == business_id,
            schema.daily_snapshots.c.snapshot_date > start_date,
            schema.daily_snapshots.c.snapshot_date <= end_date,
        )
        .order_by(schema.daily_snapshots.c.snapshot_date.asc())
    )
    rows = conn.execute(stmt).mappings().all()
    return [_row_to_snapshot(r) for r in rows]


def get_latest_snapshot(conn: Connection, business_id: int) -> DailySnapshot | None:
    stmt = (
        select(schema.daily_snapshots)
        .where(schema.daily_snapshots.c.business_id == business_id)
        .order_by(schema.daily_snapshots.c.snapshot_date.desc())
        .limit(1)
    )
    row = conn.execute(stmt).mappings().one_or_none()
    return _row_to_snapshot(row) if row else None
