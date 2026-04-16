"""Generate a city's hex grid and load it into grid_cells.

Usage:
    uv run python scripts/generate_grid.py [--city PATH]
                                           [--boundary path/to/boundary.geojson]
                                           [--dry-run] [--force]

City-specific values (bounds, center, zone radii, cell radii) come from a
TOML file — defaults to config/cities/berlin.toml. See grid/city.py for the
schema.

Without --boundary, cells are generated for the full bounding box; empty
outer cells will be pruned later by cell_activity tracking.

Refuses to insert if grid_cells already has rows; pass --force to wipe and
re-insert.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import select

from review_removal_tracker.db import schema
from review_removal_tracker.db.crud.grid import insert_cells
from review_removal_tracker.db.engine import get_connection
from review_removal_tracker.grid.city import load_city_config
from review_removal_tracker.grid.generate import generate_grid

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CITY_CONFIG = PROJECT_ROOT / "config" / "cities" / "berlin.toml"


def _load_clip_polygon(path: str):
    from shapely.geometry import shape
    from shapely.ops import unary_union

    with open(path) as f:
        data = json.load(f)

    if data.get("type") == "FeatureCollection":
        geoms = [shape(feat["geometry"]) for feat in data["features"]]
        return unary_union(geoms)
    if data.get("type") == "Feature":
        return shape(data["geometry"])
    return shape(data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--city",
        default=str(DEFAULT_CITY_CONFIG),
        help=f"Path to city config TOML (default: {DEFAULT_CITY_CONFIG})",
    )
    parser.add_argument("--boundary", help="Path to a GeoJSON file with the city admin boundary")
    parser.add_argument("--dry-run", action="store_true", help="Generate cells but do not insert")
    parser.add_argument("--force", action="store_true", help="Delete existing grid_cells before inserting")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    city = load_city_config(args.city)
    logger.info("Loaded city config: %s", city.name)

    clip_polygon = _load_clip_polygon(args.boundary) if args.boundary else None
    if clip_polygon is not None:
        logger.info("Using clip polygon from %s", args.boundary)

    cells = generate_grid(city, clip_polygon=clip_polygon)
    by_zone = Counter(c.zone for c in cells)
    logger.info(
        "Generated %d cells for %s: %d inner, %d outer",
        len(cells), city.name, by_zone["inner"], by_zone["outer"],
    )

    if args.dry_run:
        logger.info("Dry run — not inserting")
        return 0

    with get_connection() as conn:
        existing = conn.execute(select(schema.grid_cells.c.id).limit(1)).first()
        if existing is not None:
            if not args.force:
                logger.error(
                    "grid_cells already has rows. Re-run with --force to wipe and re-insert."
                )
                return 1
            # Cascades to cell_activity via FK ON DELETE CASCADE.
            conn.execute(schema.grid_cells.delete())
            logger.info("Deleted existing grid_cells (--force)")

        ids = insert_cells(conn, cells)
        logger.info("Inserted %d cells", len(ids))

    return 0


if __name__ == "__main__":
    sys.exit(main())
