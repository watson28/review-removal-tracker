"""Hex-grid generation for Nearby Search snapshot collection.

Cells are circles centered on a hex lattice covering a city's bounding box.
Inner-zone cells are denser (smaller radius); outer-zone cells are coarser.
The optional `clip_polygon` argument keeps only cells whose center lies inside
a city's admin boundary.

City-specific values (bounds, center, zone/cell radii) are passed in via a
`CityConfig` — see grid/city.py and config/cities/*.toml.
"""
from __future__ import annotations

import math
from decimal import Decimal
from typing import TYPE_CHECKING

from review_removal_tracker.db.models import GridCell
from review_removal_tracker.grid.city import CityConfig

if TYPE_CHECKING:
    from shapely.geometry.base import BaseGeometry


EARTH_RADIUS_M = 6_371_000.0
METERS_PER_DEGREE_LAT = 111_320.0


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two points, in meters."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def _meters_per_degree_lng(lat: float) -> float:
    return METERS_PER_DEGREE_LAT * math.cos(math.radians(lat))


def _hex_lattice(
    city: CityConfig,
    radius_m: int,
    zone: str,
) -> list[GridCell]:
    """Generate cells on a hex lattice over the city's bounding box.
    """
    spacing_m = radius_m * math.sqrt(3)
    ref_lat = (city.north + city.south) / 2
    spacing_lat_deg = spacing_m / METERS_PER_DEGREE_LAT
    spacing_lng_deg = spacing_m / _meters_per_degree_lng(ref_lat)
    lng_offset = spacing_lng_deg / 2

    cells: list[GridCell] = []
    lat = city.south
    row = 0
    while lat <= city.north + 1e-9:
        lng = city.west + (lng_offset if row % 2 == 1 else 0.0)
        while lng <= city.east + 1e-9:
            cells.append(GridCell(
                center_lat=Decimal(f"{lat:.6f}"),
                center_lng=Decimal(f"{lng:.6f}"),
                radius_meters=radius_m,
                zone=zone,
            ))
            lng += spacing_lng_deg
        lat += spacing_lat_deg
        row += 1
    return cells


def generate_grid(
    city: CityConfig,
    clip_polygon: "BaseGeometry | None" = None,
) -> list[GridCell]:
    """Generate the inner+outer hex grid for a city.

    Inner cells (radius_m=city.inner_cell_radius_m, zone='inner') are kept
    where the center lies within city.inner_zone_radius_m of (city.center_lat,
    city.center_lng). Outer cells (radius_m=city.outer_cell_radius_m,
    zone='outer') fill the rest of the bounding box. If `clip_polygon` is
    provided, cells whose centers fall outside it are discarded.
    """
    inner = [
        c for c in _hex_lattice(city, city.inner_cell_radius_m, "inner")
        if haversine_m(
            float(c.center_lat), float(c.center_lng),
            city.center_lat, city.center_lng,
        ) <= city.inner_zone_radius_m
    ]
    outer = [
        c for c in _hex_lattice(city, city.outer_cell_radius_m, "outer")
        if haversine_m(
            float(c.center_lat), float(c.center_lng),
            city.center_lat, city.center_lng,
        ) > city.inner_zone_radius_m
    ]

    cells = inner + outer

    if clip_polygon is not None:
        from shapely.geometry import Point
        cells = [
            c for c in cells
            if clip_polygon.contains(Point(float(c.center_lng), float(c.center_lat)))
        ]

    return cells
