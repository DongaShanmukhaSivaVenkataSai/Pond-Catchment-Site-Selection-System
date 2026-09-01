"""
DEM Builder Service
Interpolates a Digital Elevation Model grid from projected contour points.
Based on: build_dem.py
"""

import numpy as np
from scipy.interpolate import griddata
from typing import List, Dict, Any, Tuple


def build_dem(
    projected_data: Dict[str, Any],
    resolution: float = 1.0
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """
    Builds a DEM from projected contours using linear interpolation.

    Args:
        projected_data: Output from project_contours() containing 'contours'.
        resolution: Grid resolution in meters (default 1.0 m).

    Returns:
        (dem, grid_x, grid_y, resolution)
    """
    contours = projected_data["contours"]

    x_points, y_points, elevations = [], [], []

    for contour in contours:
        elev = contour["elevation"]
        for x, y in contour["coordinates"]:
            x_points.append(x)
            y_points.append(y)
            elevations.append(elev)

    x_arr = np.array(x_points)
    y_arr = np.array(y_points)
    z_arr = np.array(elevations)

    min_x, max_x = x_arr.min(), x_arr.max()
    min_y, max_y = y_arr.min(), y_arr.max()

    gx = np.arange(min_x, max_x + resolution, resolution)
    gy = np.arange(min_y, max_y + resolution, resolution)
    grid_x, grid_y = np.meshgrid(gx, gy)

    # Linear interpolation
    dem = griddata((x_arr, y_arr), z_arr, (grid_x, grid_y), method="linear")

    # Fill NaN edges with nearest
    missing = np.isnan(dem)
    if np.any(missing):
        dem_nearest = griddata(
            (x_arr, y_arr), z_arr,
            (grid_x[missing], grid_y[missing]),
            method="nearest"
        )
        dem[missing] = dem_nearest

    return dem, grid_x, grid_y, resolution
