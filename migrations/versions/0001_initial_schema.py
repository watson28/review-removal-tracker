"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "businesses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("place_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("district", sa.String(), nullable=False),
        sa.Column("lat", sa.Numeric(9, 6), nullable=False),
        sa.Column("lng", sa.Numeric(9, 6), nullable=False),
        sa.Column("first_seen", sa.Date(), server_default=sa.text("CURRENT_DATE"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("place_id"),
    )
    op.create_index("ix_businesses_category_district", "businesses", ["category", "district"])

    op.create_table(
        "daily_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("review_count", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Numeric(3, 2), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", "snapshot_date", name="uq_snapshots_business_date"),
    )
    op.create_index(
        "ix_snapshots_business_date",
        "daily_snapshots",
        ["business_id", sa.text("snapshot_date DESC")],
    )

    op.create_table(
        "computed_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("computed_date", sa.Date(), nullable=False),
        sa.Column("window_days", sa.Integer(), nullable=False),
        sa.Column("gross_additions", sa.Integer(), nullable=False),
        sa.Column("gross_removals", sa.Integer(), nullable=False),
        sa.Column("rrr", sa.Numeric(8, 4), nullable=True),
        sa.Column("rgr", sa.Numeric(8, 4), nullable=True),
        sa.Column("delta_r", sa.Numeric(8, 4), nullable=True),
        sa.Column("cri", sa.Numeric(8, 4), nullable=True),
        sa.Column("mcs", sa.Numeric(8, 4), nullable=True),
        sa.CheckConstraint("window_days IN (7, 30, 90)", name="ck_metrics_window_days"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "business_id", "computed_date", "window_days",
            name="uq_metrics_business_date_window",
        ),
    )


def downgrade() -> None:
    op.drop_table("computed_metrics")
    op.drop_index("ix_snapshots_business_date", table_name="daily_snapshots")
    op.drop_table("daily_snapshots")
    op.drop_index("ix_businesses_category_district", table_name="businesses")
    op.drop_table("businesses")
