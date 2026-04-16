import textwrap
from pathlib import Path

import pytest

from review_removal_tracker.grid.city import load_city_config


def write_toml(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "city.toml"
    p.write_text(textwrap.dedent(body).lstrip())
    return p


def test_load_berlin_config_from_repo(berlin):
    assert berlin.name == "Berlin"
    assert berlin.south < berlin.center_lat < berlin.north
    assert berlin.west < berlin.center_lng < berlin.east
    assert berlin.inner_cell_radius_m == 500
    assert berlin.outer_cell_radius_m == 1000


def test_berlin_config_has_discovery_categories_and_districts(berlin):
    assert "restaurant" in berlin.discovery_categories
    assert "Mitte" in berlin.discovery_districts
    assert len(berlin.discovery_categories) >= 3
    assert len(berlin.discovery_districts) >= 5


def test_load_minimal_config_has_empty_discovery(tmp_path):
    p = write_toml(tmp_path, """
        name = "Testopolis"
        inner_zone_radius_m = 1500.0
        inner_cell_radius_m = 200
        outer_cell_radius_m = 400

        [bounds]
        north = 41.0
        south = 40.9
        east = 2.2
        west = 2.1

        [center]
        lat = 40.95
        lng = 2.15
    """)
    c = load_city_config(p)
    assert c.discovery_categories == ()
    assert c.discovery_districts == ()


def test_load_config_with_discovery(tmp_path):
    p = write_toml(tmp_path, """
        name = "Testopolis"
        inner_zone_radius_m = 1500.0
        inner_cell_radius_m = 200
        outer_cell_radius_m = 400

        [bounds]
        north = 41.0
        south = 40.9
        east = 2.2
        west = 2.1

        [center]
        lat = 40.95
        lng = 2.15

        [discovery]
        categories = ["bar", "club"]
        districts = ["North", "South"]
    """)
    c = load_city_config(p)
    assert c.discovery_categories == ("bar", "club")
    assert c.discovery_districts == ("North", "South")


def test_load_minimal_config(tmp_path):
    p = write_toml(tmp_path, """
        name = "Testopolis"
        inner_zone_radius_m = 1500.0
        inner_cell_radius_m = 200
        outer_cell_radius_m = 400

        [bounds]
        north = 41.0
        south = 40.9
        east = 2.2
        west = 2.1

        [center]
        lat = 40.95
        lng = 2.15
    """)
    c = load_city_config(p)
    assert c.name == "Testopolis"
    assert c.inner_cell_radius_m == 200
    assert c.outer_cell_radius_m == 400
    assert c.inner_zone_radius_m == 1500.0


def test_missing_key_raises_value_error(tmp_path):
    p = write_toml(tmp_path, """
        name = "Bad"
        inner_zone_radius_m = 1000.0
        inner_cell_radius_m = 200
        outer_cell_radius_m = 400

        [bounds]
        north = 41.0
        south = 40.9
        east = 2.2
        # missing west

        [center]
        lat = 40.95
        lng = 2.15
    """)
    with pytest.raises(ValueError, match="Missing key"):
        load_city_config(p)


def test_inverted_bounds_rejected(tmp_path):
    p = write_toml(tmp_path, """
        name = "Bad"
        inner_zone_radius_m = 1000.0
        inner_cell_radius_m = 200
        outer_cell_radius_m = 400

        [bounds]
        north = 40.9
        south = 41.0
        east = 2.2
        west = 2.1

        [center]
        lat = 40.95
        lng = 2.15
    """)
    with pytest.raises(ValueError, match="north .* > south"):
        load_city_config(p)


def test_center_outside_bounds_rejected(tmp_path):
    p = write_toml(tmp_path, """
        name = "Bad"
        inner_zone_radius_m = 1000.0
        inner_cell_radius_m = 200
        outer_cell_radius_m = 400

        [bounds]
        north = 41.0
        south = 40.9
        east = 2.2
        west = 2.1

        [center]
        lat = 50.0
        lng = 2.15
    """)
    with pytest.raises(ValueError, match="center.lat"):
        load_city_config(p)


def test_negative_cell_radius_rejected(tmp_path):
    p = write_toml(tmp_path, """
        name = "Bad"
        inner_zone_radius_m = 1000.0
        inner_cell_radius_m = -1
        outer_cell_radius_m = 400

        [bounds]
        north = 41.0
        south = 40.9
        east = 2.2
        west = 2.1

        [center]
        lat = 40.95
        lng = 2.15
    """)
    with pytest.raises(ValueError, match="cell radii"):
        load_city_config(p)
