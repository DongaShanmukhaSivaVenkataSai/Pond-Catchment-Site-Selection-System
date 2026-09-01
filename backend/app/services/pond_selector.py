"""
Pond Site Selection Service
Finds and scores optimal pond locations using MCE.
Based on: find_pond_candidates.py and score_pond_candidates.py
"""

import numpy as np
from pyproj import Transformer
from typing import List, Dict, Any, Tuple

from app.services.hydrology import D8_DIRECTIONS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize(values: np.ndarray) -> np.ndarray:
    mn, mx = values.min(), values.max()
    if mx == mn:
        return np.ones_like(values)
    return (values - mn) / (mx - mn)


def _calculate_slope_degrees(dem: np.ndarray, resolution: float) -> np.ndarray:
    gy, gx = np.gradient(dem, resolution, resolution)
    return np.degrees(np.arctan(np.sqrt(gx ** 2 + gy ** 2)))


# ---------------------------------------------------------------------------
# Main functions
# ---------------------------------------------------------------------------

def find_pond_candidates(
    dem: np.ndarray,
    flow_accumulation: np.ndarray,
    grid_x: np.ndarray,
    grid_y: np.ndarray,
    resolution: float,
    flow_percentile: float = 10.0,
    max_slope_degrees: float = 10.0,
    boundary_cells: int = 2,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Returns (candidate_mask, slope_degrees).
    """
    slope_degrees = _calculate_slope_degrees(dem, resolution)
    flow_threshold = np.percentile(flow_accumulation, flow_percentile)

    candidate_mask = (
        (flow_accumulation >= flow_threshold) &
        (slope_degrees <= max_slope_degrees)
    )

    # Remove boundary cells
    candidate_mask[:boundary_cells, :] = False
    candidate_mask[-boundary_cells:, :] = False
    candidate_mask[:, :boundary_cells] = False
    candidate_mask[:, -boundary_cells:] = False

    return candidate_mask, slope_degrees


def score_and_select_pond_candidates(
    dem: np.ndarray,
    flow_accumulation: np.ndarray,
    slope_degrees: np.ndarray,
    candidate_mask: np.ndarray,
    grid_x: np.ndarray,
    grid_y: np.ndarray,
    contours_wgs84: List[Dict[str, Any]],
    top_n: int = 5,
    min_distance_m: float = 100.0,
    flow_weight: float = 0.60,
    slope_weight: float = 0.30,
    elevation_weight: float = 0.10,
) -> List[Dict[str, Any]]:
    """
    Scores and selects top_n spatially distinct pond candidates.
    Returns a list of candidate dicts with lat/lon and metrics.
    """
    rows_idx, cols_idx = np.where(candidate_mask)
    if len(rows_idx) == 0:
        raise ValueError("No pond candidates found after filtering.")

    cand_flow = flow_accumulation[rows_idx, cols_idx]
    cand_slope = slope_degrees[rows_idx, cols_idx]
    cand_elev = dem[rows_idx, cols_idx]

    flow_score = _normalize(cand_flow)
    slope_score = 1.0 - _normalize(cand_slope)
    elev_score = 1.0 - _normalize(cand_elev)

    suitability = (
        flow_weight * flow_score +
        slope_weight * slope_score +
        elevation_weight * elev_score
    )

    # Determine UTM → WGS84 transformer
    all_lon, all_lat = [], []
    for c in contours_wgs84:
        for lon, lat in c["coordinates"]:
            all_lon.append(lon)
            all_lat.append(lat)

    mean_lon = float(np.mean(all_lon))
    mean_lat = float(np.mean(all_lat))
    utm_zone = int((mean_lon + 180) // 6) + 1
    epsg = (32600 if mean_lat >= 0 else 32700) + utm_zone

    transformer = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)

    # Spatial NMS: pick top_n that are at least min_distance_m apart
    sorted_idx = np.argsort(suitability)[::-1]
    selected = []

    for idx in sorted_idx:
        r, c = int(rows_idx[idx]), int(cols_idx[idx])
        cx = float(grid_x[r, c])
        cy = float(grid_y[r, c])

        too_close = any(
            (cx - p["x_m"]) ** 2 + (cy - p["y_m"]) ** 2 < min_distance_m ** 2
            for p in selected
        )
        if too_close:
            continue

        lon, lat = transformer.transform(cx, cy)
        selected.append({
            "rank": len(selected) + 1,
            "latitude": float(lat),
            "longitude": float(lon),
            "x_m": cx,
            "y_m": cy,
            "elevation_m": float(dem[r, c]),
            "slope_degrees": float(slope_degrees[r, c]),
            "flow_accumulation_cells": float(flow_accumulation[r, c]),
            "suitability_score": float(suitability[idx]),
            "google_maps_url": f"https://www.google.com/maps?q={lat},{lon}"
        })

        if len(selected) == top_n:
            break

    return selected
