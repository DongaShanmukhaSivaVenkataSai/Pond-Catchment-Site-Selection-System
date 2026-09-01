"""
KML Parser Service
Parses a KML file and extracts contour lines with elevation and coordinates.
Based on: parser.py
"""

import xml.etree.ElementTree as ET
from typing import List, Dict, Any


NAMESPACE = {"kml": "http://www.opengis.net/kml/2.2"}


def parse_kml_bytes(kml_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Parses raw KML bytes and returns a list of contour dicts:
      [{id, elevation, coordinates: [[lon, lat], ...]}, ...]
    """
    root = ET.fromstring(kml_bytes)
    placemarks = root.findall(".//kml:Placemark", NAMESPACE)

    contours: List[Dict[str, Any]] = []

    for placemark in placemarks:
        # ID check (contours have SimpleData ID or we generate sequential ID)
        id_element = placemark.find(".//kml:SimpleData[@name='ID']", NAMESPACE)
        contour_id = int(id_element.text) if (id_element is not None and id_element.text and id_element.text.isdigit()) else len(contours) + 1

        # Elevation from <name> or SimpleData
        elevation = 0.0
        name_el = placemark.find("kml:name", NAMESPACE)
        if name_el is not None and name_el.text:
            try:
                elevation = float(name_el.text.strip())
            except ValueError:
                # Check for SimpleData elevation or ELEV
                elev_el = placemark.find(".//kml:SimpleData[@name='ELEVATION']", NAMESPACE) or \
                          placemark.find(".//kml:SimpleData[@name='elevation']", NAMESPACE) or \
                          placemark.find(".//kml:SimpleData[@name='ELEV']", NAMESPACE)
                if elev_el is not None and elev_el.text:
                    try:
                        elevation = float(elev_el.text.strip())
                    except ValueError:
                        continue
                else:
                    # Skip non-elevation placemarks (like 'land', 'sources', etc.)
                    continue

        # Coordinates
        coords_el = placemark.find(".//kml:coordinates", NAMESPACE)
        if coords_el is None or not coords_el.text:
            continue

        points = []
        for point in coords_el.text.strip().split():
            parts = point.split(",")
            if len(parts) >= 2:
                try:
                    points.append([float(parts[0]), float(parts[1])])
                except ValueError:
                    continue

        if len(points) >= 2:
            contours.append({
                "id": contour_id,
                "elevation": elevation,
                "coordinates": points
            })

    return contours


def contours_to_geojson(contours: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Converts parsed WGS84 contours list into a standard GeoJSON FeatureCollection
    containing LineString features for display on interactive web maps.
    """
    features = []
    min_elev = min((c["elevation"] for c in contours), default=0.0)
    max_elev = max((c["elevation"] for c in contours), default=0.0)

    for c in contours:
        features.append({
            "type": "Feature",
            "properties": {
                "id": c["id"],
                "elevation_m": c["elevation"],
                "point_count": len(c["coordinates"]),
            },
            "geometry": {
                "type": "LineString",
                "coordinates": c["coordinates"],
            }
        })

    return {
        "type": "FeatureCollection",
        "features": features,
        "properties": {
            "total_contours": len(contours),
            "min_elevation_m": min_elev,
            "max_elevation_m": max_elev,
        }
    }
