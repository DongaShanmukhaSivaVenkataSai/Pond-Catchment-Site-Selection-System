"""
Pipeline Orchestrator
Runs the full KML → DEM → Hydrology → Pond Site → Catchment pipeline.
"""

import math
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from pyproj import Transformer

from app.services.kml_parser import parse_kml_bytes, contours_to_geojson
from app.services.projection import project_contours, determine_utm_epsg
from app.services.dem_builder import build_dem
from app.services.terrain import calculate_slope, analyze_terrain
from app.services.hydrology import (
    calculate_flow_direction,
    calculate_flow_accumulation,
    extract_stream_network,
)
from app.services.pond_selector import (
    find_pond_candidates,
    score_and_select_pond_candidates,
)
from app.services.catchment import (
    UpstreamGraph,
    delineate_catchment,
    catchment_mask_to_geojson,
    all_catchments_to_geojson,
)
from app.services.visualizer import generate_plot_response, _png_bytes_to_base64, plot_comprehensive_dashboard


def run_full_pipeline(
    kml_bytes: bytes,
    dem_resolution_m: float = 1.0,
    flow_percentile: float = 10.0,
    max_slope_degrees: float = 10.0,
    boundary_cells: int = 2,
    top_n: int = 5,
    min_distance_m: float = 100.0,
    flow_weight: float = 0.60,
    slope_weight: float = 0.30,
    elevation_weight: float = 0.10,
    include_plots: bool = False,
    include_streams: bool = True,
    stream_threshold_percentile: float = 98.0,
) -> Dict[str, Any]:
    """
    Runs the complete analysis pipeline and returns structured results including
    DEM statistics, hydrology analysis, pond candidates, individual and unified GeoJSONs,
    stream networks, and optional base64 visualization plots.
    """
    # 1. Parse KML
    contours_wgs84 = parse_kml_bytes(kml_bytes)
    if not contours_wgs84:
        raise ValueError("No valid contour Placemarks could be parsed from the KML file.")

    #contours_geojson = contours_to_geojson(contours_wgs84)

    # 2. Project to UTM
    projected_data = project_contours(contours_wgs84)
    epsg, utm_zone, hemisphere = determine_utm_epsg(contours_wgs84)
    coord_sys = projected_data["coordinate_system"]

    # 3. Build DEM
    dem, grid_x, grid_y, resolution = build_dem(projected_data, dem_resolution_m)

    # 4. Terrain & Slope Analysis
    slope_deg, slope_pct = calculate_slope(dem, resolution)
    terrain_metrics = analyze_terrain(dem, resolution)

    # 5. Vectorized Flow Direction
    flow_dir = calculate_flow_direction(dem, resolution)

    # 6. Flow Accumulation
    flow_acc = calculate_flow_accumulation(flow_dir, dem=dem)

    # 7. Stream Network Extraction
    stream_geojson = None
    if include_streams:
        transformer_to_wgs84 = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
        stream_geojson = extract_stream_network(
            flow_acc, flow_dir, grid_x, grid_y,
            threshold_percentile=stream_threshold_percentile,
            transformer=transformer_to_wgs84,
        )

    # 8. Pond candidate identification
    candidate_mask, slope_degrees = find_pond_candidates(
        dem, flow_acc, grid_x, grid_y, resolution,
        flow_percentile, max_slope_degrees, boundary_cells
    )

    # 9. Multi-criteria scoring and spatial NMS selection
    selected_ponds = score_and_select_pond_candidates(
        dem, flow_acc, slope_degrees, candidate_mask,
        grid_x, grid_y, contours_wgs84,
        top_n, min_distance_m,
        flow_weight, slope_weight, elevation_weight,
    )

    # 10. Catchment Delineation for all selected ponds using UpstreamGraph
    upstream_graph = UpstreamGraph(flow_dir)
    catchments_output = []
    primary_mask = None

    for pond in selected_ponds:
        mask, stats = delineate_catchment(
            flow_dir, dem, grid_x, grid_y, resolution,
            pond["x_m"], pond["y_m"],
            graph=upstream_graph
        )
        if primary_mask is None:
            primary_mask = mask

        geojson = catchment_mask_to_geojson(
            mask, grid_x, grid_y, dem, resolution,
            pond["x_m"], pond["y_m"], epsg,
            stats, pond["latitude"], pond["longitude"],
            rank=pond["rank"],
            extra_properties={"suitability_score": pond["suitability_score"]}
        )
        catchments_output.append({
            "rank": pond["rank"],
            "pond_outlet": pond,
            "catchment": stats,
            "geojson": geojson,
        })

    # Combined GeoJSON FeatureCollection containing all top-N catchments & ponds
    all_catchments_geojson = all_catchments_to_geojson(catchments_output)

    # 11. Optional Visualization plots (Base64)
    plots_base64 = None
    if include_plots:
        plots_base64 = {}
        _, plots_base64["dashboard"] = generate_plot_response(
            "dashboard", dem, grid_x, grid_y, resolution,
            contours=contours_wgs84, slope_deg=slope_deg, flow_dir=flow_dir,
            flow_acc=flow_acc, candidates=selected_ponds, catchment_mask=primary_mask
        )
        _, plots_base64["dem"] = generate_plot_response("dem", dem, grid_x, grid_y, resolution)
        _, plots_base64["slope"] = generate_plot_response("slope", dem, grid_x, grid_y, resolution, slope_deg=slope_deg)
        _, plots_base64["flow_accumulation"] = generate_plot_response("flow_acc", dem, grid_x, grid_y, resolution, flow_acc=flow_acc)

    no_flow_cells = int(np.sum(flow_dir == -1))

    return {
        "status": "success",
        "dem": {
            "shape": list(dem.shape),
            "resolution_m": resolution,
            "min_elevation_m": float(dem.min()),
            "max_elevation_m": float(dem.max()),
            "mean_elevation_m": float(dem.mean()),
            "coordinate_system": coord_sys,
        },
        "hydrology": {
            "dem_shape": list(dem.shape),
            "max_flow_accumulation": float(flow_acc.max()),
            "mean_flow_accumulation": float(flow_acc.mean()),
            "cells_with_no_flow": no_flow_cells,
        },
        "terrain": terrain_metrics,
        "candidates": selected_ponds,
        "catchments": catchments_output,
        "all_catchments_geojson": all_catchments_geojson,
        "stream_network_geojson": stream_geojson,
        #"contours_geojson": contours_geojson,
        "plots_base64": plots_base64,
    }
