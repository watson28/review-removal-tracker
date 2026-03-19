from decimal import Decimal

from review_removal_tracker.db.crud.businesses import (
    deactivate_business,
    get_active_businesses,
    get_business_by_place_id,
    get_businesses_by_category_district,
    upsert_business,
)
from review_removal_tracker.db.models import Business


def make_business(
    place_id: str = "ChIJ_test_001",
    name: str = "Test Restaurant",
    category: str = "restaurant",
    district: str = "Mitte",
    lat: Decimal = Decimal("52.520008"),
    lng: Decimal = Decimal("13.404954"),
) -> Business:
    return Business(
        place_id=place_id,
        name=name,
        category=category,
        district=district,
        lat=lat,
        lng=lng,
    )


def test_upsert_business_inserts(conn):
    b = upsert_business(conn, make_business())
    assert b.id is not None
    assert b.place_id == "ChIJ_test_001"


def test_upsert_business_updates_on_conflict(conn):
    upsert_business(conn, make_business(name="Old Name"))
    updated = upsert_business(conn, make_business(name="New Name"))
    assert updated.name == "New Name"


def test_get_business_by_place_id(conn):
    upsert_business(conn, make_business())
    b = get_business_by_place_id(conn, "ChIJ_test_001")
    assert b is not None
    assert b.name == "Test Restaurant"


def test_get_business_by_place_id_not_found(conn):
    assert get_business_by_place_id(conn, "nonexistent") is None


def test_get_active_businesses(conn):
    upsert_business(conn, make_business(place_id="active_1"))
    upsert_business(conn, make_business(place_id="active_2"))
    businesses = get_active_businesses(conn)
    place_ids = {b.place_id for b in businesses}
    assert "active_1" in place_ids
    assert "active_2" in place_ids


def test_deactivate_business(conn):
    upsert_business(conn, make_business(place_id="to_deactivate"))
    deactivate_business(conn, "to_deactivate")
    active = get_active_businesses(conn)
    assert all(b.place_id != "to_deactivate" for b in active)


def test_get_businesses_by_category_district(conn):
    upsert_business(conn, make_business(place_id="p1", category="restaurant", district="Mitte"))
    upsert_business(conn, make_business(place_id="p2", category="restaurant", district="Mitte"))
    upsert_business(conn, make_business(place_id="p3", category="hotel", district="Mitte"))

    results = get_businesses_by_category_district(conn, "restaurant", "Mitte")
    place_ids = {b.place_id for b in results}
    assert "p1" in place_ids
    assert "p2" in place_ids
    assert "p3" not in place_ids
