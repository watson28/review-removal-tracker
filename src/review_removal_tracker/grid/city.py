"""City configuration for hex-grid generation.

A city is described by a TOML file at config/cities/<name>.toml. See
config/cities/berlin.toml for the canonical example.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CityConfig:
    name: str
    north: float
    south: float
    east: float
    west: float
    center_lat: float
    center_lng: float
    inner_zone_radius_m: float
    inner_cell_radius_m: int
    outer_cell_radius_m: int
    discovery_categories: tuple[str, ...] = ()
    discovery_districts: tuple[str, ...] = ()


def load_city_config(path: Path | str) -> CityConfig:
    p = Path(path)
    with p.open("rb") as f:
        data = tomllib.load(f)

    discovery = data.get("discovery", {})
    try:
        bounds = data["bounds"]
        center = data["center"]
        config = CityConfig(
            name=data["name"],
            north=float(bounds["north"]),
            south=float(bounds["south"]),
            east=float(bounds["east"]),
            west=float(bounds["west"]),
            center_lat=float(center["lat"]),
            center_lng=float(center["lng"]),
            inner_zone_radius_m=float(data["inner_zone_radius_m"]),
            inner_cell_radius_m=int(data["inner_cell_radius_m"]),
            outer_cell_radius_m=int(data["outer_cell_radius_m"]),
            discovery_categories=tuple(str(c) for c in discovery.get("categories", [])),
            discovery_districts=tuple(str(d) for d in discovery.get("districts", [])),
        )
    except KeyError as e:
        raise ValueError(f"Missing key {e} in city config {p}") from e

    if config.north <= config.south:
        raise ValueError(f"north ({config.north}) must be > south ({config.south})")
    if config.east <= config.west:
        raise ValueError(f"east ({config.east}) must be > west ({config.west})")
    if not (config.south <= config.center_lat <= config.north):
        raise ValueError("center.lat must lie within [south, north]")
    if not (config.west <= config.center_lng <= config.east):
        raise ValueError("center.lng must lie within [west, east]")
    if config.inner_zone_radius_m <= 0:
        raise ValueError("inner_zone_radius_m must be positive")
    if config.inner_cell_radius_m <= 0 or config.outer_cell_radius_m <= 0:
        raise ValueError("cell radii must be positive")

    return config
