"""
Unit and service-level tests for Pond Detection services.
"""

import os
import pytest
import numpy as np

from app.services.kml_parser import parse_kml_bytes, contours_to_geojson
from app.services.projection import determine_utm_epsg, project_contours
from app.services.dem_builder import build_dem
from app.services.terrain import calculate_slope, calculate_aspect, analyze_terrain
from app.services.hydrology import (
    calculate_flow_direction,
    calculate_flow_accumulation,
    extract_stream_network,
    D8_DIRECTIONS,
)
from app.services.pond_selector import find_pond_candidates, score_and_select_pond_candidates
from app.services.catchment import UpstreamGraph, delineate_catchment, catchment_mask_to_geojson


@pytest.fixture
def sample_kml_bytes():
    path = os.path.join(os.path.dirname(__file__), "..", "contours_1m.kml")
    with open(path, "rb") as f:
        return f.read()


def test_parse_kml_and_geojson(sample_kml_bytes):
    contours = parse_kml_bytes(sample_kml_bytes)
    assert len(contours) > 0
    assert "elevation" in contours[0]
    assert "coordinates" in contours[0]
    assert len(contours[0]["coordinates"]) >= 2

    geojson = contours_to_geojson(contours)
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == len(contours)
    assert geojson["features"][0]["geometry"]["type"] == "LineString"


def test_projection_and_utm(sample_kml_bytes):
    contours = parse_kml_bytes(sample_kml_bytes)
    epsg, utm_zone, hemisphere = determine_utm_epsg(contours)
    assert utm_zone == 44
    assert hemisphere == "north"
    assert epsg == 32644

    projected = project_contours(contours)
    assert projected["coordinate_system"]["target"] == "EPSG:32644"
    assert len(projected["contours"]) == len(contours)


def test_dem_builder(sample_kml_bytes):
    contours = parse_kml_bytes(sample_kml_bytes)
    projected = project_contours(contours)
    dem, grid_x, grid_y, res = build_dem(projected, resolution=2.0)

    assert dem.ndim == 2
    assert dem.shape == grid_x.shape == grid_y.shape
    assert res == 2.0
    assert not np.isnan(dem).any()
    assert dem.min() >= 200.0
    assert dem.max() <= 400.0


def test_terrain_analysis():
    # Synthetic planar surface sloping south
    dem = np.array([
        [10.0, 10.0, 10.0],
        [ 5.0,  5.0,  5.0],
        [ 0.0,  0.0,  0.0],
    ], dtype=np.float64)

    slope_deg, slope_pct = calculate_slope(dem, resolution=1.0)
    assert slope_deg.shape == dem.shape
    assert slope_deg.min() >= 0.0

    terrain_stats = analyze_terrain(dem, resolution=1.0)
    assert "elevation" in terrain_stats
    assert "slope_degrees" in terrain_stats
    assert "classification" in terrain_stats


def test_vectorized_flow_direction_and_accumulation():
    # Simple valley: flow drains to center bottom (row 2, col 1)
    dem = np.array([
        [10.0,  8.0, 10.0],
        [ 8.0,  4.0,  8.0],
        [ 6.0,  2.0,  6.0],
    ], dtype=np.float64)

    flow_dir = calculate_flow_direction(dem, resolution=1.0)
    assert flow_dir.shape == dem.shape
    # Top-left cell (0,0) with elev 10 should drain toward center (1,1) with elev 4 (dir 7 = SE)
    assert flow_dir[0, 0] == 7

    flow_acc = calculate_flow_accumulation(flow_dir, dem=dem)
    assert flow_acc.shape == dem.shape
    # Outlet cell at (2, 1) should accumulate water from upstream cells
    assert flow_acc[2, 1] > 1.0


def test_pond_candidate_selection(sample_kml_bytes):
    contours = parse_kml_bytes(sample_kml_bytes)
    projected = project_contours(contours)
    dem, grid_x, grid_y, res = build_dem(projected, resolution=2.0)
    flow_dir = calculate_flow_direction(dem, res)
    flow_acc = calculate_flow_accumulation(flow_dir, dem=dem)

    candidate_mask, slope_deg = find_pond_candidates(dem, flow_acc, grid_x, grid_y, res)
    assert np.any(candidate_mask)

    selected = score_and_select_pond_candidates(
        dem, flow_acc, slope_deg, candidate_mask, grid_x, grid_y, contours, top_n=3, min_distance_m=100.0
    )
    assert len(selected) == 3
    assert selected[0]["rank"] == 1
    assert 0.0 <= selected[0]["suitability_score"] <= 1.0
    assert "google_maps_url" in selected[0]


def test_catchment_delineation(sample_kml_bytes):
    contours = parse_kml_bytes(sample_kml_bytes)
    projected = project_contours(contours)
    epsg, _, _ = determine_utm_epsg(contours)
    dem, grid_x, grid_y, res = build_dem(projected, resolution=2.0)
    flow_dir = calculate_flow_direction(dem, res)
    flow_acc = calculate_flow_accumulation(flow_dir, dem=dem)

    cand_mask, slope_deg = find_pond_candidates(dem, flow_acc, grid_x, grid_y, res)
    selected = score_and_select_pond_candidates(dem, flow_acc, slope_deg, cand_mask, grid_x, grid_y, contours, top_n=1)
    
    pond = selected[0]
    graph = UpstreamGraph(flow_dir)
    mask, stats = delineate_catchment(flow_dir, dem, grid_x, grid_y, res, pond["x_m"], pond["y_m"], graph=graph)
    
    assert np.sum(mask) > 0
    assert stats["cell_count"] == int(np.sum(mask))
    assert stats["area_hectares"] > 0

    geojson = catchment_mask_to_geojson(
        mask, grid_x, grid_y, dem, res, pond["x_m"], pond["y_m"], epsg, stats, pond["latitude"], pond["longitude"]
    )
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == 2  # Catchment polygon + Pond point

