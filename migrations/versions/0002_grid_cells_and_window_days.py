"""grid_cells, cell_activity, and window_days (14, 30, 90)

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "grid_cells",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("center_lat", sa.Numeric(9, 6), nullable=False),
        sa.Column("center_lng", sa.Numeric(9, 6), nullable=False),
        sa.Column("radius_meters", sa.Integer(), server_default=sa.text("500"), nullable=False),
        sa.Column("district", sa.String(), nullable=True),
        sa.Column("zone", sa.String(), server_default=sa.text("'inner'"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.CheckConstraint("zone IN ('inner', 'outer')", name="ck_grid_cells_zone"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_grid_cells_active", "grid_cells", ["is_active"])

    op.create_table(
        "cell_activity",
        sa.Column("cell_id", sa.Integer(), nullable=False),
        sa.Column("last_hit_date", sa.Date(), nullable=True),
        sa.Column("hit_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(["cell_id"], ["grid_cells.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("cell_id"),
    )

    op.drop_constraint("ck_metrics_window_days", "computed_metrics", type_="check")
    op.create_check_constraint(
        "ck_metrics_window_days",
        "computed_metrics",
        "window_days IN (14, 30, 90)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_metrics_window_days", "computed_metrics", type_="check")
    op.create_check_constraint(
        "ck_metrics_window_days",
        "computed_metrics",
        "window_days IN (7, 30, 90)",
    )

    op.drop_table("cell_activity")
    op.drop_index("ix_grid_cells_active", table_name="grid_cells")
    op.drop_table("grid_cells")
