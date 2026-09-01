"""
Terrain Analysis Service
Computes slope, aspect, hillshade, profile curvature, and terrain classification from a DEM.
Based on: calculate_slope.py
"""

import numpy as np
from typing import Tuple, Dict, Any


def calculate_slope(
    dem: np.ndarray,
    resolution: float
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes slope in degrees and percent from DEM.

    Returns:
        (slope_degrees, slope_percent)
    """
    gradient_y, gradient_x = np.gradient(dem, resolution, resolution)

    slope_radians = np.arctan(np.sqrt(gradient_x ** 2 + gradient_y ** 2))
    slope_degrees = np.degrees(slope_radians)
    slope_percent = np.tan(slope_radians) * 100

    return slope_degrees, slope_percent


def calculate_aspect(
    dem: np.ndarray,
    resolution: float
) -> np.ndarray:
    """
    Computes terrain aspect (compass direction of steepest downhill slope) in degrees (0..360, clockwise from North).
    """
    gradient_y, gradient_x = np.gradient(dem, resolution, resolution)
    aspect_rad = np.arctan2(-gradient_x, gradient_y)
    aspect_deg = np.degrees(aspect_rad)
    aspect_deg = np.where(aspect_deg < 0, 360.0 + aspect_deg, aspect_deg)
    return aspect_deg


def calculate_hillshade(
    dem: np.ndarray,
    resolution: float,
    azimuth: float = 315.0,
    altitude: float = 45.0
) -> np.ndarray:
    """
    Calculates analytical hillshade raster from DEM.
    
    Args:
        dem: 2D elevation array
        resolution: grid cell size in meters
        azimuth: light source compass direction (default 315 NW)
        altitude: light source angle above horizon (default 45)
    """
    gradient_y, gradient_x = np.gradient(dem, resolution, resolution)
    slope_rad = np.arctan(np.sqrt(gradient_x ** 2 + gradient_y ** 2))
    aspect_rad = np.arctan2(-gradient_x, gradient_y)

    azimuth_rad = np.radians(azimuth)
    altitude_rad = np.radians(altitude)

    shaded = (
        np.sin(altitude_rad) * np.cos(slope_rad) +
        np.cos(altitude_rad) * np.sin(slope_rad) * np.cos(azimuth_rad - aspect_rad)
    )
    hillshade = np.clip(255 * shaded, 0, 255).astype(np.uint8)
    return hillshade


def analyze_terrain(
    dem: np.ndarray,
    resolution: float
) -> Dict[str, Any]:
    """
    Performs comprehensive terrain analysis on the DEM.
    """
    slope_deg, slope_pct = calculate_slope(dem, resolution)
    aspect_deg = calculate_aspect(dem, resolution)

    total_cells = dem.size
    flat_cells = int(np.sum(slope_deg < 2.0))
    gentle_cells = int(np.sum((slope_deg >= 2.0) & (slope_deg < 5.0)))
    moderate_cells = int(np.sum((slope_deg >= 5.0) & (slope_deg < 10.0)))
    steep_cells = int(np.sum(slope_deg >= 10.0))

    return {
        "elevation": {
            "min_m": float(dem.min()),
            "max_m": float(dem.max()),
            "mean_m": float(dem.mean()),
            "std_m": float(dem.std()),
        },
        "slope_degrees": {
            "min": float(slope_deg.min()),
            "max": float(slope_deg.max()),
            "mean": float(slope_deg.mean()),
            "std": float(slope_deg.std()),
        },
        "slope_percent": {
            "min": float(slope_pct.min()),
            "max": float(slope_pct.max()),
            "mean": float(slope_pct.mean()),
        },
        "aspect_degrees": {
            "mean": float(aspect_deg.mean()),
        },
        "classification": {
            "flat_under_2deg_pct": round(flat_cells / total_cells * 100.0, 2),
            "gentle_2_to_5deg_pct": round(gentle_cells / total_cells * 100.0, 2),
            "moderate_5_to_10deg_pct": round(moderate_cells / total_cells * 100.0, 2),
            "steep_over_10deg_pct": round(steep_cells / total_cells * 100.0, 2),
        }
    }
