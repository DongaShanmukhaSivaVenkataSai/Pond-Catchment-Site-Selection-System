"""
Projection Service
Projects WGS84 (lon/lat) contour coordinates to UTM metric CRS.
Based on: projected.py
"""

import math
from typing import List, Dict, Any, Tuple
from pyproj import Transformer


def determine_utm_epsg(contours: List[Dict[str, Any]]) -> Tuple[int, int, str]:
    """
    Given a list of contours (WGS84), determine the best UTM EPSG code.
    Returns (epsg, utm_zone, hemisphere).
    """
    all_lon = []
    all_lat = []
    for contour in contours:
        for lon, lat in contour["coordinates"]:
            all_lon.append(lon)
            all_lat.append(lat)

    if not all_lon:
        raise ValueError("No coordinates found in contours.")

    mean_lon = sum(all_lon) / len(all_lon)
    mean_lat = sum(all_lat) / len(all_lat)

    utm_zone = math.floor((mean_lon + 180) / 6) + 1
    hemisphere = "north" if mean_lat >= 0 else "south"
    epsg = (32600 if mean_lat >= 0 else 32700) + utm_zone

    return epsg, utm_zone, hemisphere


def project_contours(contours: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Projects each contour's coordinates from WGS84 → UTM.
    Returns a dict with coordinate_system metadata and projected contours.
    """
    epsg, utm_zone, hemisphere = determine_utm_epsg(contours)

    transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)

    projected_contours = []
    for contour in contours:
        projected_coords = []
        for lon, lat in contour["coordinates"]:
            x, y = transformer.transform(lon, lat)
            projected_coords.append([x, y])

        projected_contours.append({
            "id": contour["id"],
            "elevation": contour["elevation"],
            "coordinates": projected_coords
        })

    return {
        "coordinate_system": {
            "source": "EPSG:4326",
            "target": f"EPSG:{epsg}",
            "projection": "UTM",
            "utm_zone": utm_zone,
            "hemisphere": hemisphere,
            "units": "meters"
        },
        "contours": projected_contours
    }
