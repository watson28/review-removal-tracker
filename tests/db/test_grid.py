from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from review_removal_tracker.db.crud.grid import (
    deactivate_cell,
    get_active_cells,
    get_cell_activity,
    insert_cells,
    record_cell_hit,
)
from review_removal_tracker.db.models import GridCell


def make_cell(
    lat: str = "52.520000",
    lng: str = "13.405000",
    radius_meters: int = 500,
    zone: str = "inner",
    district: str | None = "Mitte",
    is_active: bool = True,
) -> GridCell:
    return GridCell(
        center_lat=Decimal(lat),
        center_lng=Decimal(lng),
        radius_meters=radius_meters,
        zone=zone,
        district=district,
        is_active=is_active,
    )


def _insert_one(conn, **overrides) -> int:
    cell = make_cell(**overrides)
    [cell_id] = insert_cells(conn, [cell])
    return cell_id


def test_insert_cells_inserts_multiple(conn):
    ids = insert_cells(conn, [
        make_cell(lat="52.520000", lng="13.405000", zone="inner"),
        make_cell(lat="52.530000", lng="13.410000", zone="inner"),
        make_cell(lat="52.450000", lng="13.500000", radius_meters=1000, zone="outer"),
    ])
    assert len(ids) == 3
    assert all(i is not None for i in ids)
    cells = get_active_cells(conn)
    assert len(cells) == 3


def test_insert_cells_empty_returns_empty(conn):
    assert insert_cells(conn, []) == []


def test_insert_cells_rejects_invalid_zone(conn):
    with pytest.raises(IntegrityError):
        insert_cells(conn, [make_cell(zone="middle")])


def test_get_active_cells_excludes_inactive(conn):
    cell_id = _insert_one(conn, lat="52.521000", lng="13.401000")
    deactivate_cell(conn, cell_id)
    assert get_active_cells(conn) == []


def test_deactivate_cell_marks_activity_inactive(conn):
    cell_id = _insert_one(conn)
    record_cell_hit(conn, cell_id, date(2026, 4, 16), hits=3)

    deactivate_cell(conn, cell_id)
    activity = get_cell_activity(conn, cell_id)
    assert activity is not None
    assert activity.is_active is False


def test_record_cell_hit_inserts_then_increments(conn):
    cell_id = _insert_one(conn)
    a1 = record_cell_hit(conn, cell_id, date(2026, 4, 16), hits=4)
    assert a1.hit_count == 4
    assert a1.last_hit_date == date(2026, 4, 16)

    a2 = record_cell_hit(conn, cell_id, date(2026, 4, 18), hits=2)
    assert a2.hit_count == 6
    assert a2.last_hit_date == date(2026, 4, 18)


def test_record_cell_hit_zero_hits_does_not_advance_last_hit_date(conn):
    cell_id = _insert_one(conn)
    record_cell_hit(conn, cell_id, date(2026, 4, 16), hits=2)
    a = record_cell_hit(conn, cell_id, date(2026, 4, 18), hits=0)
    assert a.hit_count == 2
    assert a.last_hit_date == date(2026, 4, 16)


def test_record_cell_hit_zero_hits_initial_row(conn):
    cell_id = _insert_one(conn)
    a = record_cell_hit(conn, cell_id, date(2026, 4, 16), hits=0)
    assert a.hit_count == 0
    assert a.last_hit_date is None


def test_get_cell_activity_none_when_missing(conn):
    cell_id = _insert_one(conn)
    assert get_cell_activity(conn, cell_id) is None


def test_grid_cell_district_can_be_null(conn):
    ids = insert_cells(conn, [make_cell(district=None)])
    assert len(ids) == 1
    cells = get_active_cells(conn)
    assert cells[0].district is None
