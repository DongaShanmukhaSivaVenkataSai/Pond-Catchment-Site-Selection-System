"""
extract_pond_geojson.py

Extracts a single pond rank's catchment + outlet GeoJSON
from a full /api/v1/analyze response, so you can drop it
straight into geojson.io.

Usage:
    python3 extract_pond_geojson.py response.json --rank 1 -o rank1_pond.geojson
    python3 extract_pond_geojson.py response.json --rank 2 -o rank2_pond.geojson

    # Extract all ranks at once into separate files:
    python3 extract_pond_geojson.py response.json --all -o pond
    # -> writes pond_rank1.geojson, pond_rank2.geojson, ...
"""

import argparse
import json
import sys


def load_response(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def extract_rank(data: dict, rank: int) -> dict:
    """Return the FeatureCollection (catchment + pond point) for a given rank."""
    catchments = data.get("catchments", [])
    for entry in catchments:
        if entry.get("rank") == rank:
            geojson = entry.get("geojson")
            if geojson is None:
                raise ValueError(f"Rank {rank} found but has no 'geojson' field.")
            return geojson
    available = [c.get("rank") for c in catchments]
    raise ValueError(f"Rank {rank} not found. Available ranks: {available}")


def main():
    parser = argparse.ArgumentParser(description="Extract pond catchment GeoJSON by rank.")
    parser.add_argument("response_file", help="Path to the /analyze response JSON file")
    parser.add_argument("--rank", type=int, help="Pond rank to extract (1 = best)")
    parser.add_argument("--all", action="store_true", help="Extract all ranks into separate files")
    parser.add_argument("-o", "--output", required=True,
                         help="Output file path (single rank) or filename prefix (--all)")
    args = parser.parse_args()

    if not args.rank and not args.all:
        print("Error: specify either --rank N or --all", file=sys.stderr)
        sys.exit(1)

    data = load_response(args.response_file)

    if args.all:
        catchments = data.get("catchments", [])
        if not catchments:
            print("No catchments found in response.", file=sys.stderr)
            sys.exit(1)
        for entry in catchments:
            rank = entry["rank"]
            geojson = entry["geojson"]
            out_path = f"{args.output}_rank{rank}.geojson"
            with open(out_path, "w") as f:
                json.dump(geojson, f, indent=2)
            n_features = len(geojson.get("features", []))
            print(f"Wrote {out_path} ({n_features} features)")
    else:
        geojson = extract_rank(data, args.rank)
        with open(args.output, "w") as f:
            json.dump(geojson, f, indent=2)
        n_features = len(geojson.get("features", []))
        print(f"Wrote {args.output} ({n_features} features)")


if __name__ == "__main__":
    main()
