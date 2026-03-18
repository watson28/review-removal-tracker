from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    UniqueConstraint,
    ForeignKey,
    Index,
    text,
)

metadata = MetaData()

businesses = Table(
    "businesses",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("place_id", String, nullable=False, unique=True),
    Column("name", String, nullable=False),
    Column("category", String, nullable=False),
    Column("district", String, nullable=False),
    Column("lat", Numeric(9, 6), nullable=False),
    Column("lng", Numeric(9, 6), nullable=False),
    Column("first_seen", Date, nullable=False, server_default=text("CURRENT_DATE")),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
)

Index("ix_businesses_category_district", businesses.c.category, businesses.c.district)

daily_snapshots = Table(
    "daily_snapshots",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("business_id", Integer, ForeignKey("businesses.id"), nullable=False),
    Column("snapshot_date", Date, nullable=False),
    Column("review_count", Integer, nullable=False),
    Column("rating", Numeric(3, 2), nullable=False),
    UniqueConstraint("business_id", "snapshot_date", name="uq_snapshots_business_date"),
)

Index(
    "ix_snapshots_business_date",
    daily_snapshots.c.business_id,
    daily_snapshots.c.snapshot_date.desc(),
)

computed_metrics = Table(
    "computed_metrics",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("business_id", Integer, ForeignKey("businesses.id"), nullable=False),
    Column("computed_date", Date, nullable=False),
    Column("window_days", Integer, nullable=False),
    Column("gross_additions", Integer, nullable=False),
    Column("gross_removals", Integer, nullable=False),
    Column("rrr", Numeric(8, 4), nullable=True),
    Column("rgr", Numeric(8, 4), nullable=True),
    Column("delta_r", Numeric(8, 4), nullable=True),
    Column("cri", Numeric(8, 4), nullable=True),
    Column("mcs", Numeric(8, 4), nullable=True),
    UniqueConstraint(
        "business_id", "computed_date", "window_days",
        name="uq_metrics_business_date_window",
    ),
    CheckConstraint("window_days IN (7, 30, 90)", name="ck_metrics_window_days"),
)
