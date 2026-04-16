from datetime import date
from typing import Any

from sqlalchemy import Connection, select
from sqlalchemy.dialects.postgresql import insert

from review_removal_tracker.db import schema
from review_removal_tracker.db.models import CellActivity, GridCell


def _row_to_cell(row) -> GridCell:
    return GridCell(
        id=row.id,
        center_lat=row.center_lat,
        center_lng=row.center_lng,
        radius_meters=row.radius_meters,
        district=row.district,
        zone=row.zone,
        is_active=row.is_active,
    )


def _row_to_activity(row) -> CellActivity:
    return CellActivity(
        cell_id=row.cell_id,
        last_hit_date=row.last_hit_date,
        hit_count=row.hit_count,
        is_active=row.is_active,
    )


def insert_cells(conn: Connection, cells: list[GridCell]) -> list[int]:
    if not cells:
        return []
    stmt = (
        schema.grid_cells.insert()
        .values([
            {
                "center_lat": c.center_lat,
                "center_lng": c.center_lng,
                "radius_meters": c.radius_meters,
                "district": c.district,
                "zone": c.zone,
                "is_active": c.is_active,
            }
            for c in cells
        ])
        .returning(schema.grid_cells.c.id)
    )
    return [row.id for row in conn.execute(stmt)]


def get_active_cells(conn: Connection) -> list[GridCell]:
    stmt = select(schema.grid_cells).where(schema.grid_cells.c.is_active.is_(True))
    rows = conn.execute(stmt).mappings().all()
    return [_row_to_cell(r) for r in rows]


def deactivate_cell(conn: Connection, cell_id: int) -> None:
    conn.execute(
        schema.grid_cells.update()
        .where(schema.grid_cells.c.id == cell_id)
        .values(is_active=False)
    )
    conn.execute(
        schema.cell_activity.update()
        .where(schema.cell_activity.c.cell_id == cell_id)
        .values(is_active=False)
    )


def record_cell_hit(
    conn: Connection,
    cell_id: int,
    hit_date: date,
    hits: int,
) -> CellActivity:
    """Increment hit_count by `hits`; update last_hit_date only when hits > 0."""
    base = {
        "cell_id": cell_id,
        "last_hit_date": hit_date if hits > 0 else None,
        "hit_count": hits,
        "is_active": True,
    }
    set_: dict[str, Any] = {"hit_count": schema.cell_activity.c.hit_count + hits}
    if hits > 0:
        set_["last_hit_date"] = hit_date
    stmt = (
        insert(schema.cell_activity)
        .values(**base)
        .on_conflict_do_update(index_elements=["cell_id"], set_=set_)
        .returning(schema.cell_activity)
    )
    row = conn.execute(stmt).mappings().one()
    return _row_to_activity(row)


def get_cell_activity(conn: Connection, cell_id: int) -> CellActivity | None:
    stmt = select(schema.cell_activity).where(schema.cell_activity.c.cell_id == cell_id)
    row = conn.execute(stmt).mappings().one_or_none()
    return _row_to_activity(row) if row else None
