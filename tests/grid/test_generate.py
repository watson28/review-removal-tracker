import math
from dataclasses import replace

from shapely.geometry import Point, Polygon

from review_removal_tracker.grid.generate import generate_grid, haversine_m


def test_haversine_zero_distance():
    assert haversine_m(52.52, 13.40, 52.52, 13.40) == 0.0


def test_haversine_known_distance():
    # Brandenburg Gate ~ Alexanderplatz, ~2.2 km apart.
    d = haversine_m(52.5163, 13.3777, 52.5219, 13.4132)
    assert 2000 < d < 2500


def test_grid_inner_cells_use_inner_radius(berlin):
    cells = generate_grid(berlin)
    inner = [c for c in cells if c.zone == "inner"]
    assert all(c.radius_meters == berlin.inner_cell_radius_m for c in inner)


def test_grid_outer_cells_use_outer_radius(berlin):
    cells = generate_grid(berlin)
    outer = [c for c in cells if c.zone == "outer"]
    assert all(c.radius_meters == berlin.outer_cell_radius_m for c in outer)


def test_grid_zones_partition_by_distance_from_center(berlin):
    cells = generate_grid(berlin)
    for c in cells:
        d = haversine_m(
            float(c.center_lat), float(c.center_lng),
            berlin.center_lat, berlin.center_lng,
        )
        if c.zone == "inner":
            assert d <= berlin.inner_zone_radius_m
        else:
            assert d > berlin.inner_zone_radius_m


def test_grid_all_cells_within_bounding_box(berlin):
    cells = generate_grid(berlin)
    for c in cells:
        lat, lng = float(c.center_lat), float(c.center_lng)
        assert berlin.south <= lat <= berlin.north
        assert berlin.west <= lng <= berlin.east


def test_grid_no_inner_outer_overlap_at_zone_boundary(berlin):
    cells = generate_grid(berlin)
    inner_centers = {(c.center_lat, c.center_lng) for c in cells if c.zone == "inner"}
    outer_centers = {(c.center_lat, c.center_lng) for c in cells if c.zone == "outer"}
    assert inner_centers.isdisjoint(outer_centers)


def test_grid_clip_polygon_removes_cells_outside(berlin):
    # A tiny polygon around the city center: only a handful of cells should survive.
    eps = 0.01  # ~1.1 km in lat
    poly = Polygon([
        (berlin.center_lng - eps, berlin.center_lat - eps),
        (berlin.center_lng + eps, berlin.center_lat - eps),
        (berlin.center_lng + eps, berlin.center_lat + eps),
        (berlin.center_lng - eps, berlin.center_lat + eps),
    ])
    full = generate_grid(berlin)
    clipped = generate_grid(berlin, clip_polygon=poly)
    assert 0 < len(clipped) < len(full)
    for c in clipped:
        assert poly.contains(Point(float(c.center_lng), float(c.center_lat)))


def test_grid_cell_spacing_matches_radius_sqrt3(berlin):
    # Per spec: spacing between adjacent cell centers = radius * sqrt(3).
    cells = [c for c in generate_grid(berlin) if c.zone == "inner"]
    expected = berlin.inner_cell_radius_m * math.sqrt(3)

    closest = float("inf")
    for i, a in enumerate(cells):
        for b in cells[i + 1:]:
            d = haversine_m(
                float(a.center_lat), float(a.center_lng),
                float(b.center_lat), float(b.center_lng),
            )
            if 0 < d < closest:
                closest = d
    # ±10% tolerance: lat/lng → meters has small projection error across Berlin.
    assert 0.9 * expected <= closest <= 1.1 * expected


def test_grid_custom_inner_zone_radius_changes_partition(berlin):
    big = replace(berlin, inner_zone_radius_m=10000.0)
    small = replace(berlin, inner_zone_radius_m=2000.0)
    big_count = sum(1 for c in generate_grid(big) if c.zone == "inner")
    small_count = sum(1 for c in generate_grid(small) if c.zone == "inner")
    assert big_count > small_count


def test_grid_works_for_arbitrary_city():
    # A made-up "city" — just to prove the generator has no Berlin coupling.
    from review_removal_tracker.grid.city import CityConfig

    fakeville = CityConfig(
        name="Fakeville",
        north=40.05, south=39.95,
        east=-74.95, west=-75.05,
        center_lat=40.00, center_lng=-75.00,
        inner_zone_radius_m=2000.0,
        inner_cell_radius_m=300,
        outer_cell_radius_m=600,
    )
    cells = generate_grid(fakeville)
    assert len(cells) > 0
    assert any(c.zone == "inner" for c in cells)
    assert any(c.zone == "outer" for c in cells)
    inner_radii = {c.radius_meters for c in cells if c.zone == "inner"}
    outer_radii = {c.radius_meters for c in cells if c.zone == "outer"}
    assert inner_radii == {300}
    assert outer_radii == {600}
