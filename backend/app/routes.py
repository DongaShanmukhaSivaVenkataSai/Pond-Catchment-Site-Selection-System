"""
Pond Detection (PD) API Routes
Full REST API suite for watershed analysis, terrain modeling, pond site selection, and GeoJSON GIS integration.
"""

import asyncio
import io
import csv
import numpy as np
from fastapi import APIRouter, UploadFile, File, Query, HTTPException, Response, Form
from fastapi.responses import JSONResponse, Response as FastAPIResponse
from typing import Optional, List, Dict, Any

from app.pipeline import run_full_pipeline
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
    delineate_custom_catchment,
    catchment_mask_to_geojson,
    all_catchments_to_geojson,
)
from app.services.visualizer import generate_plot_response
from app.schemas import (
    ParseResponse,
    DemStats,
    HydrologyStats,
    TerrainAnalysisResponse,
    PondCandidatesResponse,
    CatchmentResponse,
    StreamNetworkResponse,
    VisualizationResponse,
    FullPipelineResponse,
    GeoJSONFeatureCollection,
)

router = APIRouter(prefix="/api/v1", tags=["Pond Catchment Analysis"])


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@router.get("/health", summary="Health Check")
async def health():
    """Returns API health status."""
    return {"status": "ok", "service": "Pond Detection (PD) Backend", "version": "1.0.0"}


# ---------------------------------------------------------------------------
# Step 1: Parse KML & Contours GeoJSON
# ---------------------------------------------------------------------------

@router.post(
    "/parse",
    response_model=ParseResponse,
    summary="Parse KML/KMZ Contour File",
    description="Accepts a KML file upload, parses contour Placemarks, and returns elevation + coordinate data.",
)
async def parse_kml(file: UploadFile = File(..., description="KML contour file")):
    if not file.filename.lower().endswith((".kml", ".kmz")):
        raise HTTPException(status_code=400, detail="Only .kml or .kmz files are accepted.")

    kml_bytes = await file.read()
    try:
        contours = parse_kml_bytes(kml_bytes)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse KML: {e}")

    if not contours:
        raise HTTPException(status_code=422, detail="No valid contour Placemarks found in file.")

    return {
        "status": "success",
        "contour_count": len(contours),
        "sample": contours[:3],
        "geojson": None,
    }


@router.post(
    "/contours/geojson",
    summary="Get Contours as WGS84 GeoJSON",
    description="Parses KML file and returns all contour lines as a standard GeoJSON FeatureCollection of LineStrings.",
)
async def contours_geojson_endpoint(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".kml", ".kmz")):
        raise HTTPException(status_code=400, detail="Only .kml or .kmz files are accepted.")

    kml_bytes = await file.read()
    try:
        contours = parse_kml_bytes(kml_bytes)
        if not contours:
            raise HTTPException(status_code=422, detail="No valid contours found in KML.")
        geojson = contours_to_geojson(contours)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return JSONResponse(content=geojson)


# ---------------------------------------------------------------------------
# Step 2: Build DEM & Terrain Analysis
# ---------------------------------------------------------------------------

@router.post(
    "/dem",
    response_model=DemStats,
    summary="Build DEM from KML contours",
    description="Parses KML, projects coordinates to UTM, and interpolates a DEM grid.",
)
async def build_dem_endpoint(
    file: UploadFile = File(...),
    resolution_m: float = Query(default=1.0, gt=0, description="DEM grid resolution in meters"),
):
    kml_bytes = await file.read()
    try:
        contours = parse_kml_bytes(kml_bytes)
        if not contours:
            raise HTTPException(status_code=422, detail="No contours found in KML.")
        projected_data = project_contours(contours)
        dem, grid_x, grid_y, resolution = build_dem(projected_data, resolution_m)
        coord_sys = projected_data["coordinate_system"]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "shape": list(dem.shape),
        "resolution_m": resolution,
        "min_elevation_m": float(dem.min()),
        "max_elevation_m": float(dem.max()),
        "mean_elevation_m": float(dem.mean()),
        "coordinate_system": coord_sys,
    }


@router.post(
    "/terrain",
    response_model=TerrainAnalysisResponse,
    summary="Terrain & Slope Analysis",
    description="Computes slope degrees, slope percent, aspect, and terrain slope classification percentages.",
)
async def terrain_endpoint(
    file: UploadFile = File(...),
    resolution_m: float = Query(default=1.0, gt=0, description="DEM resolution in meters"),
):
    kml_bytes = await file.read()
    try:
        contours = parse_kml_bytes(kml_bytes)
        projected_data = project_contours(contours)
        dem, grid_x, grid_y, resolution = build_dem(projected_data, resolution_m)
        terrain_stats = analyze_terrain(dem, resolution)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "status": "success",
        **terrain_stats,
    }


# ---------------------------------------------------------------------------
# Step 3: Hydrology & Drainage Streams
# ---------------------------------------------------------------------------

@router.post(
    "/hydrology",
    response_model=HydrologyStats,
    summary="Compute Flow Direction & Accumulation",
    description="Computes D8 flow direction and flow accumulation grids using vectorized kernels.",
)
async def hydrology_endpoint(
    file: UploadFile = File(...),
    resolution_m: float = Query(default=1.0, gt=0),
):
    kml_bytes = await file.read()
    try:
        contours = parse_kml_bytes(kml_bytes)
        projected_data = project_contours(contours)
        dem, grid_x, grid_y, resolution = build_dem(projected_data, resolution_m)
        
        loop = asyncio.get_event_loop()
        flow_dir = await loop.run_in_executor(None, calculate_flow_direction, dem, resolution)
        flow_acc = await loop.run_in_executor(None, lambda: calculate_flow_accumulation(flow_dir, dem=dem))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "dem_shape": list(dem.shape),
        "max_flow_accumulation": float(flow_acc.max()),
        "mean_flow_accumulation": float(flow_acc.mean()),
        "cells_with_no_flow": int(np.sum(flow_dir == -1)),
    }


@router.post(
    "/streams/geojson",
    response_model=StreamNetworkResponse,
    summary="Extract Drainage Stream Network as GeoJSON",
    description="Identifies major flow accumulation channels and converts them to WGS84 GeoJSON LineStrings.",
)
async def streams_geojson_endpoint(
    file: UploadFile = File(...),
    resolution_m: float = Query(default=1.0, gt=0),
    threshold_percentile: float = Query(default=98.0, ge=50.0, le=100.0, description="Percentile threshold for channel extraction"),
):
    kml_bytes = await file.read()
    try:
        contours = parse_kml_bytes(kml_bytes)
        projected_data = project_contours(contours)
        epsg, _, _ = determine_utm_epsg(contours)
        dem, grid_x, grid_y, resolution = build_dem(projected_data, resolution_m)
        
        flow_dir = calculate_flow_direction(dem, resolution)
        flow_acc = calculate_flow_accumulation(flow_dir, dem=dem)

        from pyproj import Transformer
        transformer = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
        stream_geojson = extract_stream_network(
            flow_acc, flow_dir, grid_x, grid_y,
            threshold_percentile=threshold_percentile,
            transformer=transformer,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "status": "success",
        "threshold_percentile": threshold_percentile,
        "total_segments": stream_geojson["properties"]["total_segments"],
        "geojson": stream_geojson,
    }


# ---------------------------------------------------------------------------
# Step 4: Pond Site Candidates (MCE)
# ---------------------------------------------------------------------------

@router.post(
    "/pond-candidates",
    response_model=PondCandidatesResponse,
    summary="Find and Score Optimal Pond Candidates",
    description="Identifies top-N spatially distinct pond candidates using Multi-Criteria Evaluation (MCE) and Spatial NMS.",
)
async def pond_candidates_endpoint(
    file: UploadFile = File(...),
    resolution_m: float = Query(default=1.0, gt=0),
    flow_percentile: float = Query(default=10.0, ge=0, le=100),
    max_slope_degrees: float = Query(default=10.0, gt=0),
    boundary_cells: int = Query(default=2, ge=0),
    top_n: int = Query(default=5, ge=1, le=20),
    min_distance_m: float = Query(default=100.0, gt=0),
    flow_weight: float = Query(default=0.60, ge=0, le=1),
    slope_weight: float = Query(default=0.30, ge=0, le=1),
    elevation_weight: float = Query(default=0.10, ge=0, le=1),
):
    kml_bytes = await file.read()
    try:
        contours = parse_kml_bytes(kml_bytes)
        projected_data = project_contours(contours)
        dem, grid_x, grid_y, resolution = build_dem(projected_data, resolution_m)

        flow_dir = calculate_flow_direction(dem, resolution)
        flow_acc = calculate_flow_accumulation(flow_dir, dem=dem)

        candidate_mask, slope_degrees = find_pond_candidates(
            dem, flow_acc, grid_x, grid_y, resolution,
            flow_percentile, max_slope_degrees, boundary_cells
        )
        selected = score_and_select_pond_candidates(
            dem, flow_acc, slope_degrees, candidate_mask,
            grid_x, grid_y, contours,
            top_n, min_distance_m,
            flow_weight, slope_weight, elevation_weight,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "status": "success",
        "top_candidates_count": len(selected),
        "min_separation_distance_m": min_distance_m,
        "weights": {
            "flow_weight": flow_weight,
            "slope_weight": slope_weight,
            "elevation_weight": elevation_weight,
        },
        "candidates": selected,
    }


# ---------------------------------------------------------------------------
# Step 5: Catchment Delineation (Rank-based & Custom coordinate)
# ---------------------------------------------------------------------------

@router.post(
    "/catchment",
    response_model=CatchmentResponse,
    summary="Delineate Catchment for Ranked Pond Site",
    description="Delineates watershed catchment boundary and metrics for a specific ranked pond.",
)
async def catchment_endpoint(
    file: UploadFile = File(...),
    resolution_m: float = Query(default=1.0, gt=0),
    flow_percentile: float = Query(default=10.0, ge=0, le=100),
    max_slope_degrees: float = Query(default=10.0, gt=0),
    boundary_cells: int = Query(default=2, ge=0),
    top_n: int = Query(default=5, ge=1, le=20),
    min_distance_m: float = Query(default=100.0, gt=0),
    pond_rank: int = Query(default=1, ge=1, description="Rank of the pond candidate to delineate (1 = best)"),
):
    kml_bytes = await file.read()
    try:
        contours = parse_kml_bytes(kml_bytes)
        projected_data = project_contours(contours)
        epsg, _, _ = determine_utm_epsg(contours)
        dem, grid_x, grid_y, resolution = build_dem(projected_data, resolution_m)

        flow_dir = calculate_flow_direction(dem, resolution)
        flow_acc = calculate_flow_accumulation(flow_dir, dem=dem)

        candidate_mask, slope_degrees = find_pond_candidates(
            dem, flow_acc, grid_x, grid_y, resolution,
            flow_percentile, max_slope_degrees, boundary_cells
        )
        selected = score_and_select_pond_candidates(
            dem, flow_acc, slope_degrees, candidate_mask,
            grid_x, grid_y, contours,
            top_n, min_distance_m,
        )

        if pond_rank > len(selected):
            raise HTTPException(
                status_code=404,
                detail=f"Only {len(selected)} pond candidates found; rank {pond_rank} not available."
            )

        pond = selected[pond_rank - 1]
        graph = UpstreamGraph(flow_dir)
        mask, stats = delineate_catchment(
            flow_dir, dem, grid_x, grid_y, resolution,
            pond["x_m"], pond["y_m"],
            graph=graph
        )
        geojson = catchment_mask_to_geojson(
            mask, grid_x, grid_y, dem, resolution,
            pond["x_m"], pond["y_m"], epsg,
            stats, pond["latitude"], pond["longitude"],
            rank=pond_rank,
            extra_properties={"suitability_score": pond["suitability_score"]}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "status": "success",
        "pond_rank": pond_rank,
        "pond_outlet": pond,
        "catchment": stats,
        "geojson": geojson,
    }


@router.post(
    "/catchment/custom",
    response_model=CatchmentResponse,
    summary="Delineate Catchment for Custom Geographic Point",
    description="Delineates watershed catchment upstream of an arbitrary user-specified latitude/longitude or UTM coordinates.",
)
async def custom_catchment_endpoint(
    file: UploadFile = File(...),
    latitude: Optional[float] = Query(default=None, description="WGS84 Latitude"),
    longitude: Optional[float] = Query(default=None, description="WGS84 Longitude"),
    x_m: Optional[float] = Query(default=None, description="UTM Easting (meters)"),
    y_m: Optional[float] = Query(default=None, description="UTM Northing (meters)"),
    resolution_m: float = Query(default=1.0, gt=0),
):
    if (latitude is None or longitude is None) and (x_m is None or y_m is None):
        raise HTTPException(status_code=400, detail="Must provide either (latitude, longitude) or (x_m, y_m).")

    kml_bytes = await file.read()
    try:
        contours = parse_kml_bytes(kml_bytes)
        projected_data = project_contours(contours)
        epsg, _, _ = determine_utm_epsg(contours)
        dem, grid_x, grid_y, resolution = build_dem(projected_data, resolution_m)

        flow_dir = calculate_flow_direction(dem, resolution)
        mask, stats, geojson = delineate_custom_catchment(
            flow_dir, dem, grid_x, grid_y, resolution, epsg,
            latitude=latitude, longitude=longitude, x_m=x_m, y_m=y_m
        )
        outlet_dict = {
            "latitude": latitude,
            "longitude": longitude,
            "x_m": x_m,
            "y_m": y_m,
            "elevation_m": stats.get("outlet_elevation_m"),
            "google_maps_url": f"https://www.google.com/maps?q={latitude},{longitude}" if latitude else "",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "status": "success",
        "pond_rank": None,
        "pond_outlet": outlet_dict,
        "catchment": stats,
        "geojson": geojson,
    }


@router.post(
    "/catchments/all",
    summary="Get All Top-N Catchments as Unified GeoJSON",
    description="Runs analysis and returns all top-N delineated catchments and pond points in a single GeoJSON FeatureCollection.",
)
async def all_catchments_geojson_endpoint(
    file: UploadFile = File(...),
    resolution_m: float = Query(default=1.0, gt=0),
    top_n: int = Query(default=5, ge=1, le=20),
    min_distance_m: float = Query(default=100.0, gt=0),
):
    kml_bytes = await file.read()
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: run_full_pipeline(
                kml_bytes=kml_bytes,
                dem_resolution_m=resolution_m,
                top_n=top_n,
                min_distance_m=min_distance_m,
                include_plots=False,
            )
        )
        all_geojson = result["all_catchments_geojson"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return JSONResponse(content=all_geojson)


# ---------------------------------------------------------------------------
# Step 6: Map Visualizations (PNG & Base64)
# ---------------------------------------------------------------------------

@router.post(
    "/visualize/{plot_type}",
    summary="Generate Hydrological Map Plot (PNG or Base64)",
    description="Generates Matplotlib visualizations: 'contours', 'dem', 'slope', 'flow-direction', 'flow-accumulation', 'candidates', 'catchment', or 'dashboard'. Pass format='png' for raw image stream or format='json' for base64.",
)
async def visualize_endpoint(
    plot_type: str,
    file: UploadFile = File(...),
    resolution_m: float = Query(default=1.0, gt=0),
    format: str = Query(default="png", enum=["png", "json"], description="Output format: 'png' binary image or 'json' base64"),
):
    kml_bytes = await file.read()
    try:
        contours = parse_kml_bytes(kml_bytes)
        projected_data = project_contours(contours)
        dem, grid_x, grid_y, resolution = build_dem(projected_data, resolution_m)

        slope_deg, _ = calculate_slope(dem, resolution)
        flow_dir = calculate_flow_direction(dem, resolution)
        flow_acc = calculate_flow_accumulation(flow_dir, dem=dem)

        candidate_mask, _ = find_pond_candidates(dem, flow_acc, grid_x, grid_y, resolution)
        selected = score_and_select_pond_candidates(
            dem, flow_acc, slope_deg, candidate_mask, grid_x, grid_y, contours
        )

        primary_mask = None
        if selected:
            primary_mask, _ = delineate_catchment(
                flow_dir, dem, grid_x, grid_y, resolution,
                selected[0]["x_m"], selected[0]["y_m"]
            )

        png_bytes, b64 = generate_plot_response(
            plot_type=plot_type,
            dem=dem,
            grid_x=grid_x,
            grid_y=grid_y,
            resolution=resolution,
            contours=contours,
            slope_deg=slope_deg,
            flow_dir=flow_dir,
            flow_acc=flow_acc,
            candidates=selected,
            catchment_mask=primary_mask,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if format == "json":
        return {
            "status": "success",
            "plot_type": plot_type,
            "image_base64": b64,
            "content_type": "image/png",
        }
    else:
        return FastAPIResponse(content=png_bytes, media_type="image/png")


# ---------------------------------------------------------------------------
# Step 7: CSV Data Export
# ---------------------------------------------------------------------------

@router.post(
    "/export/csv",
    summary="Export Pond Candidates & Catchment Statistics as CSV",
    description="Runs analysis and returns a downloadable CSV table with candidate metrics and watershed areas.",
)
async def export_csv_endpoint(
    file: UploadFile = File(...),
    resolution_m: float = Query(default=1.0, gt=0),
    top_n: int = Query(default=5, ge=1, le=20),
    min_distance_m: float = Query(default=100.0, gt=0),
):
    kml_bytes = await file.read()
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: run_full_pipeline(
                kml_bytes=kml_bytes,
                dem_resolution_m=resolution_m,
                top_n=top_n,
                min_distance_m=min_distance_m,
            )
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Rank", "Latitude", "Longitude", "UTM_X_m", "UTM_Y_m",
            "Elevation_m", "Slope_degrees", "Flow_Accumulation_cells",
            "Suitability_Score", "Catchment_Area_m2", "Catchment_Area_hectares",
            "Catchment_Min_Elev_m", "Catchment_Max_Elev_m", "Google_Maps_URL"
        ])

        for c, catch in zip(result["candidates"], result["catchments"]):
            stat = catch["catchment"]
            writer.writerow([
                c["rank"],
                f"{c['latitude']:.6f}",
                f"{c['longitude']:.6f}",
                f"{c['x_m']:.1f}",
                f"{c['y_m']:.1f}",
                f"{c['elevation_m']:.2f}",
                f"{c['slope_degrees']:.2f}",
                f"{c['flow_accumulation_cells']:.0f}",
                f"{c['suitability_score']:.4f}",
                f"{stat['area_m2']:.1f}",
                f"{stat['area_hectares']:.4f}",
                f"{stat['min_elevation_m']:.1f}",
                f"{stat['max_elevation_m']:.1f}",
                c["google_maps_url"],
            ])

        csv_content = output.getvalue()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return FastAPIResponse(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=pond_candidates_summary.csv"}
    )


# ---------------------------------------------------------------------------
# Step 8: Full Pipeline (Single-Call End-to-End)
# ---------------------------------------------------------------------------

@router.post(
    "/analyze",
    response_model=FullPipelineResponse,
    summary="Full End-to-End Hydrological Pipeline",
    description="Executes the complete pipeline: KML Parse → UTM Projection → DEM Interpolation → Terrain Analysis → D8 Hydrology → MCE Pond Selection → Watershed Catchment Delineation → GeoJSON Exports.",
)

async def full_pipeline_endpoint(
    contour_map: UploadFile = File(...),
    resolution_m: float = Query(default=1.0, gt=0, description="DEM resolution in meters"),
    flow_percentile: float = Query(default=10.0, ge=0, le=100),
    max_slope_degrees: float = Query(default=10.0, gt=0),
    boundary_cells: int = Query(default=2, ge=0),
    top_n: int = Query(default=2, ge=1, le=20),
    min_distance_m: float = Query(default=100.0, gt=0),
    flow_weight: float = Query(default=0.60, ge=0, le=1),
    slope_weight: float = Query(default=0.30, ge=0, le=1),
    elevation_weight: float = Query(default=0.10, ge=0, le=1),
    include_plots: bool = Query(default=False, description="Whether to include base64 visualization plots in response"),
    include_streams: bool = Query(default=False, description="Whether to include stream drainage network GeoJSON"),
):
    if not contour_map.filename.lower().endswith((".kml", ".kmz")):
        raise HTTPException(status_code=400, detail="Only .kml or .kmz files are accepted.")

    kml_bytes = await contour_map.read()

    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: run_full_pipeline(
                kml_bytes=kml_bytes,
                dem_resolution_m=resolution_m,
                flow_percentile=flow_percentile,
                max_slope_degrees=max_slope_degrees,
                boundary_cells=boundary_cells,
                top_n=top_n,
                min_distance_m=min_distance_m,
                flow_weight=flow_weight,
                slope_weight=slope_weight,
                elevation_weight=elevation_weight,
                include_plots=include_plots,
                include_streams=include_streams,
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return JSONResponse(content=result)
