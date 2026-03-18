from datetime import date
from decimal import Decimal

from review_removal_tracker.db.crud.businesses import upsert_business
from review_removal_tracker.db.crud.metrics import (
    get_latest_metrics,
    get_metrics_for_leaderboard,
    upsert_metrics,
    upsert_metrics_bulk,
)
from review_removal_tracker.db.models import Business, ComputedMetrics


def make_business(conn, place_id="ChIJ_metrics_test", category="restaurant", district="Mitte") -> int:
    b = upsert_business(
        conn,
        Business(
            place_id=place_id,
            name="Metrics Test",
            category=category,
            district=district,
            lat=Decimal("52.52"),
            lng=Decimal("13.40"),
        ),
    )
    return b.id


def make_metrics(business_id: int, **kwargs) -> ComputedMetrics:
    defaults = dict(
        business_id=business_id,
        computed_date=date(2026, 1, 31),
        window_days=30,
        gross_additions=40,
        gross_removals=12,
        rrr=Decimal("0.0300"),
        rgr=Decimal("0.3000"),
        delta_r=Decimal("0.0125"),
        cri=Decimal("2.0000"),
        mcs=Decimal("45.0000"),
    )
    defaults.update(kwargs)
    return ComputedMetrics(**defaults)


def test_upsert_metrics_inserts(conn):
    bid = make_business(conn)
    m = upsert_metrics(conn, make_metrics(bid))
    assert m.id is not None
    assert m.mcs == Decimal("45.0000")


def test_upsert_metrics_is_idempotent(conn):
    bid = make_business(conn, "idempotent_metrics")
    upsert_metrics(conn, make_metrics(bid, mcs=Decimal("45.0")))
    m = upsert_metrics(conn, make_metrics(bid, mcs=Decimal("60.0")))
    assert m.mcs == Decimal("60.0000")


def test_get_latest_metrics(conn):
    bid = make_business(conn, "latest_metrics")
    upsert_metrics(conn, make_metrics(bid, computed_date=date(2026, 1, 15), mcs=Decimal("30.0")))
    upsert_metrics(conn, make_metrics(bid, computed_date=date(2026, 1, 31), mcs=Decimal("45.0")))

    m = get_latest_metrics(conn, bid, window_days=30)
    assert m.computed_date == date(2026, 1, 31)
    assert m.mcs == Decimal("45.0000")


def test_get_latest_metrics_none(conn):
    bid = make_business(conn, "no_metrics")
    assert get_latest_metrics(conn, bid, window_days=30) is None


def test_upsert_metrics_bulk(conn):
    bid = make_business(conn, "bulk_metrics")
    metrics_list = [
        make_metrics(bid, computed_date=date(2026, 1, i), window_days=30)
        for i in [7, 14, 21, 28]
    ]
    count = upsert_metrics_bulk(conn, metrics_list)
    assert count == 4


def test_get_metrics_for_leaderboard(conn):
    bid1 = make_business(conn, "leader_1", category="restaurant", district="Mitte")
    bid2 = make_business(conn, "leader_2", category="restaurant", district="Mitte")
    bid3 = make_business(conn, "leader_3", category="hotel", district="Mitte")

    d = date(2026, 1, 31)
    upsert_metrics(conn, make_metrics(bid1, computed_date=d, mcs=Decimal("80.0")))
    upsert_metrics(conn, make_metrics(bid2, computed_date=d, mcs=Decimal("30.0")))
    upsert_metrics(conn, make_metrics(bid3, computed_date=d, mcs=Decimal("50.0")))

    results = get_metrics_for_leaderboard(conn, window_days=30, computed_date=d)
    assert len(results) == 3
    # sorted by MCS descending
    assert results[0][1].mcs == Decimal("80.0000")
    assert results[1][1].mcs == Decimal("50.0000")
    assert results[2][1].mcs == Decimal("30.0000")


def test_get_metrics_for_leaderboard_filter_category(conn):
    bid1 = make_business(conn, "filter_cat_1", category="restaurant", district="Mitte")
    bid2 = make_business(conn, "filter_cat_2", category="hotel", district="Mitte")

    d = date(2026, 1, 31)
    upsert_metrics(conn, make_metrics(bid1, computed_date=d))
    upsert_metrics(conn, make_metrics(bid2, computed_date=d))

    results = get_metrics_for_leaderboard(conn, window_days=30, computed_date=d, category="restaurant")
    assert len(results) == 1
    assert results[0][0].category == "restaurant"
