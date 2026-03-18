from datetime import date

from sqlalchemy import Connection, select
from sqlalchemy.dialects.postgresql import insert

from review_removal_tracker.db import schema
from review_removal_tracker.db.models import Business, ComputedMetrics


def _row_to_metrics(row) -> ComputedMetrics:
    return ComputedMetrics(
        id=row.id,
        business_id=row.business_id,
        computed_date=row.computed_date,
        window_days=row.window_days,
        gross_additions=row.gross_additions,
        gross_removals=row.gross_removals,
        rrr=row.rrr,
        rgr=row.rgr,
        delta_r=row.delta_r,
        cri=row.cri,
        mcs=row.mcs,
    )


def upsert_metrics(conn: Connection, metrics: ComputedMetrics) -> ComputedMetrics:
    stmt = (
        insert(schema.computed_metrics)
        .values(
            business_id=metrics.business_id,
            computed_date=metrics.computed_date,
            window_days=metrics.window_days,
            gross_additions=metrics.gross_additions,
            gross_removals=metrics.gross_removals,
            rrr=metrics.rrr,
            rgr=metrics.rgr,
            delta_r=metrics.delta_r,
            cri=metrics.cri,
            mcs=metrics.mcs,
        )
        .on_conflict_do_update(
            constraint="uq_metrics_business_date_window",
            set_={
                "gross_additions": metrics.gross_additions,
                "gross_removals": metrics.gross_removals,
                "rrr": metrics.rrr,
                "rgr": metrics.rgr,
                "delta_r": metrics.delta_r,
                "cri": metrics.cri,
                "mcs": metrics.mcs,
            },
        )
        .returning(schema.computed_metrics)
    )
    row = conn.execute(stmt).mappings().one()
    return _row_to_metrics(row)


def upsert_metrics_bulk(conn: Connection, metrics_list: list[ComputedMetrics]) -> int:
    if not metrics_list:
        return 0
    count = 0
    for metrics in metrics_list:
        upsert_metrics(conn, metrics)
        count += 1
    return count


def get_latest_metrics(
    conn: Connection, business_id: int, window_days: int
) -> ComputedMetrics | None:
    stmt = (
        select(schema.computed_metrics)
        .where(
            schema.computed_metrics.c.business_id == business_id,
            schema.computed_metrics.c.window_days == window_days,
        )
        .order_by(schema.computed_metrics.c.computed_date.desc())
        .limit(1)
    )
    row = conn.execute(stmt).mappings().one_or_none()
    return _row_to_metrics(row) if row else None


def get_metrics_for_leaderboard(
    conn: Connection,
    window_days: int,
    computed_date: date,
    category: str | None = None,
    district: str | None = None,
) -> list[tuple[Business, ComputedMetrics]]:
    from review_removal_tracker.db.crud.businesses import _row_to_business

    b = schema.businesses
    m = schema.computed_metrics

    stmt = (
        select(b, m)
        .join(m, b.c.id == m.c.business_id)
        .where(
            m.c.window_days == window_days,
            m.c.computed_date == computed_date,
            b.c.is_active.is_(True),
        )
        .order_by(m.c.mcs.desc().nullslast())
    )

    if category:
        stmt = stmt.where(b.c.category == category)
    if district:
        stmt = stmt.where(b.c.district == district)

    rows = conn.execute(stmt).mappings().all()

    results = []
    for row in rows:
        business = Business(
            id=row["id"],
            place_id=row["place_id"],
            name=row["name"],
            category=row["category"],
            district=row["district"],
            lat=row["lat"],
            lng=row["lng"],
            first_seen=row["first_seen"],
            is_active=row["is_active"],
        )
        metrics = ComputedMetrics(
            id=row["id_1"] if "id_1" in row else None,
            business_id=row["business_id"],
            computed_date=row["computed_date"],
            window_days=row["window_days"],
            gross_additions=row["gross_additions"],
            gross_removals=row["gross_removals"],
            rrr=row["rrr"],
            rgr=row["rgr"],
            delta_r=row["delta_r"],
            cri=row["cri"],
            mcs=row["mcs"],
        )
        results.append((business, metrics))

    return results
