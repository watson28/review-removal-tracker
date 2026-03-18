from sqlalchemy import Connection, select
from sqlalchemy.dialects.postgresql import insert

from review_removal_tracker.db import schema
from review_removal_tracker.db.models import Business


def _row_to_business(row) -> Business:
    return Business(
        id=row.id,
        place_id=row.place_id,
        name=row.name,
        category=row.category,
        district=row.district,
        lat=row.lat,
        lng=row.lng,
        first_seen=row.first_seen,
        is_active=row.is_active,
    )


def upsert_business(conn: Connection, business: Business) -> Business:
    stmt = (
        insert(schema.businesses)
        .values(
            place_id=business.place_id,
            name=business.name,
            category=business.category,
            district=business.district,
            lat=business.lat,
            lng=business.lng,
        )
        .on_conflict_do_update(
            index_elements=["place_id"],
            set_={
                "name": business.name,
                "category": business.category,
                "district": business.district,
                "lat": business.lat,
                "lng": business.lng,
                "is_active": business.is_active,
            },
        )
        .returning(schema.businesses)
    )
    row = conn.execute(stmt).mappings().one()
    return _row_to_business(row)


def get_business_by_place_id(conn: Connection, place_id: str) -> Business | None:
    stmt = select(schema.businesses).where(schema.businesses.c.place_id == place_id)
    row = conn.execute(stmt).mappings().one_or_none()
    return _row_to_business(row) if row else None


def get_active_businesses(conn: Connection) -> list[Business]:
    stmt = select(schema.businesses).where(schema.businesses.c.is_active.is_(True))
    rows = conn.execute(stmt).mappings().all()
    return [_row_to_business(r) for r in rows]


def deactivate_business(conn: Connection, place_id: str) -> None:
    stmt = (
        schema.businesses.update()
        .where(schema.businesses.c.place_id == place_id)
        .values(is_active=False)
    )
    conn.execute(stmt)


def get_businesses_by_category_district(
    conn: Connection, category: str, district: str
) -> list[Business]:
    stmt = select(schema.businesses).where(
        schema.businesses.c.category == category,
        schema.businesses.c.district == district,
        schema.businesses.c.is_active.is_(True),
    )
    rows = conn.execute(stmt).mappings().all()
    return [_row_to_business(r) for r in rows]
