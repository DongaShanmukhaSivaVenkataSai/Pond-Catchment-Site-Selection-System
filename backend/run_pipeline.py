"""
Pond Detection (PD) CLI & Pipeline Runner
Executes the full hydrological and pond site selection pipeline from the command line.

Usage:
  python run_pipeline.py [KML_FILE] [OPTIONS]

Example:
  python run_pipeline.py contours_1m.kml --resolution 1.0 --top-n 5 --output-dir ./results --plot
"""

import os
import sys
import json
import argparse
import numpy as np

from app.pipeline import run_full_pipeline
from app.services.kml_parser import parse_kml_bytes
from app.services.projection import project_contours, determine_utm_epsg
from app.services.dem_builder import build_dem
from app.services.terrain import calculate_slope
from app.services.hydrology import calculate_flow_direction, calculate_flow_accumulation
from app.services.pond_selector import find_pond_candidates, score_and_select_pond_candidates
from app.services.catchment import UpstreamGraph, delineate_catchment, catchment_mask_to_geojson
from app.services.visualizer import generate_plot_response


def main():
    parser = argparse.ArgumentParser(
        description="Pond Detection & Watershed Catchment Analysis CLI"
    )
    parser.add_argument(
        "kml_file",
        nargs="?",
        default="contours_1m.kml",
        help="Path to input KML/KMZ contour file (default: contours_1m.kml)"
    )
    parser.add_argument(
        "--resolution", "-r",
        type=float,
        default=1.0,
        help="DEM grid resolution in meters (default: 1.0)"
    )
    parser.add_argument(
        "--top-n", "-n",
        type=int,
        default=5,
        help="Number of optimal pond sites to identify (default: 5)"
    )
    parser.add_argument(
        "--min-distance", "-d",
        type=float,
        default=100.0,
        help="Minimum spatial separation between candidate sites in meters (default: 100.0)"
    )
    parser.add_argument(
        "--max-slope",
        type=float,
        default=10.0,
        help="Maximum slope threshold in degrees (default: 10.0)"
    )
    parser.add_argument(
        "--flow-percentile",
        type=float,
        default=10.0,
        help="Flow accumulation percentile threshold (default: 10.0)"
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default="./output",
        help="Directory to save output files and deliverables (default: ./output)"
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Generate and save PNG visualization plots"
    )

    args = parser.parse_args()

    if not os.path.exists(args.kml_file):
        print(f"Error: Input file '{args.kml_file}' not found.")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    print("=" * 70)
    print(" POND DETECTION & WATERSHED CATCHMENT PIPELINE")
    print("=" * 70)
    print(f"Input file : {args.kml_file}")
    print(f"Resolution : {args.resolution} m")
    print(f"Top N sites: {args.top_n}")
    print(f"Output dir : {args.output_dir}")
    print("-" * 70)

    with open(args.kml_file, "rb") as f:
        kml_bytes = f.read()

    print("Running end-to-end hydrological analysis...")
    results = run_full_pipeline(
        kml_bytes=kml_bytes,
        dem_resolution_m=args.resolution,
        flow_percentile=args.flow_percentile,
        max_slope_degrees=args.max_slope,
        top_n=args.top_n,
        min_distance_m=args.min_distance,
        include_plots=args.plot,
        include_streams=True,
    )

    # Save deliverables
    summary_json_path = os.path.join(args.output_dir, "pipeline_summary.json")
    with open(summary_json_path, "w") as f:
        json.dump({
            "dem": results["dem"],
            "hydrology": results["hydrology"],
            "terrain": results["terrain"],
            "candidates": results["candidates"],
            "catchments_count": len(results["catchments"]),
        }, f, indent=2)

    catchments_geojson_path = os.path.join(args.output_dir, "catchments.geojson")
    with open(catchments_geojson_path, "w") as f:
        json.dump(results["all_catchments_geojson"], f, indent=2)

    contours_geojson_path = os.path.join(args.output_dir, "contours.geojson")
    with open(contours_geojson_path, "w") as f:
        json.dump(results["contours_geojson"], f, indent=2)

    if results.get("stream_network_geojson"):
        streams_geojson_path = os.path.join(args.output_dir, "streams.geojson")
        with open(streams_geojson_path, "w") as f:
            json.dump(results["stream_network_geojson"], f, indent=2)

    # Save top candidate JSONs (backward compatibility with root scripts)
    top_5_json_path = os.path.join(args.output_dir, "top_5_pond_candidates.json")
    with open(top_5_json_path, "w") as f:
        json.dump({"candidates": results["candidates"]}, f, indent=2)

    print("\n" + "=" * 70)
    print(f" TOP {len(results['candidates'])} OPTIMAL POND SITES IDENTIFIED")
    print("=" * 70)

    for cand, catch in zip(results["candidates"], results["catchments"]):
        stat = catch["catchment"]
        print(f"\n[RANK #{cand['rank']}] Suitability Score: {cand['suitability_score'] * 100:.1f}%")
        print(f"  Coordinates:     Lat {cand['latitude']:.6f}, Lon {cand['longitude']:.6f} (UTM X={cand['x_m']:.1f}, Y={cand['y_m']:.1f})")
        print(f"  Terrain:         Elevation = {cand['elevation_m']:.1f} m | Slope = {cand['slope_degrees']:.2f}°")
        print(f"  Hydrology:       Flow Accumulation = {cand['flow_accumulation_cells']:.0f} cells")
        print(f"  Catchment Area:  {stat['area_hectares']:.2f} ha ({stat['area_m2']:,.0f} m²)")
        print(f"  Elevation Range: {stat['min_elevation_m']:.1f} m to {stat['max_elevation_m']:.1f} m (Mean: {stat['mean_elevation_m']:.1f} m)")
        print(f"  Google Maps:     {cand['google_maps_url']}")

    print("\n" + "=" * 70)
    print(f"Saved summary JSON to:       {summary_json_path}")
    print(f"Saved catchments GeoJSON to: {catchments_geojson_path}")
    print(f"Saved contours GeoJSON to:   {contours_geojson_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()

