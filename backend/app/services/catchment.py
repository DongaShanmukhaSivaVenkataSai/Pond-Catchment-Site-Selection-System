"""
Catchment Delineation Service
Delineates watershed catchments upstream of pond outlet cells or arbitrary coordinates using fast reverse-flow graph traversal.
Converts catchment masks to high-performance GeoJSON polygons.
"""

import numpy as np
from pyproj import Transformer
from shapely.geometry import box
from shapely.ops import unary_union
from typing import List, Dict, Any, Tuple, Optional

from app.services.hydrology import D8_DIRECTIONS


class UpstreamGraph:
    """
    High-speed CSR-like inverted flow graph using flat NumPy arrays.
    Enables sub-millisecond BFS upstream watershed delineation.
    """
    def __init__(self, flow_direction: np.ndarray):
        rows, cols = flow_direction.shape
        n_cells = rows * cols
        self.rows = rows
        self.cols = cols
        self.n_cells = n_cells

        flat_fdir = flow_direction.ravel()
        dr_map = np.array([d[0] for d in D8_DIRECTIONS], dtype=np.int32)
        dc_map = np.array([d[1] for d in D8_DIRECTIONS], dtype=np.int32)

        r_grid, c_grid = np.indices((rows, cols), dtype=np.int32)
        flat_r = r_grid.ravel()
        flat_c = c_grid.ravel()

        valid_flow = flat_fdir >= 0
        valid_dirs = flat_fdir[valid_flow]

        target_r = flat_r[valid_flow] + dr_map[valid_dirs]
        target_c = flat_c[valid_flow] + dc_map[valid_dirs]

        in_bounds = (target_r >= 0) & (target_r < rows) & (target_c >= 0) & (target_c < cols)

        srcs = np.where(valid_flow)[0][in_bounds]
        dsts = target_r[in_bounds] * cols + target_c[in_bounds]

        if len(dsts) > 0:
            sort_idx = np.argsort(dsts)
            self.sorted_dsts = dsts[sort_idx]
            self.sorted_srcs = srcs[sort_idx]

            unique_dsts, split_idx = np.unique(self.sorted_dsts, return_index=True)
            self.offsets = np.zeros(n_cells, dtype=np.int32)
            self.offsets[unique_dsts] = split_idx
            counts = np.diff(np.append(split_idx, len(self.sorted_srcs)))
            self.counts = np.zeros(n_cells, dtype=np.int32)
            self.counts[unique_dsts] = counts
        else:
            self.sorted_srcs = np.array([], dtype=np.int32)
            self.offsets = np.zeros(n_cells, dtype=np.int32)
            self.counts = np.zeros(n_cells, dtype=np.int32)

    def trace_upstream(self, start_r: int, start_c: int) -> np.ndarray:
        """Returns boolean mask of shape (rows, cols) of upstream draining cells."""
        outlet = start_r * self.cols + start_c
        mask = np.zeros(self.n_cells, dtype=bool)
        stack = [outlet]

        sorted_srcs = self.sorted_srcs
        offsets = self.offsets
        counts = self.counts

        while stack:
            curr = stack.pop()
            if mask[curr]:
                continue
            mask[curr] = True
            cnt = counts[curr]
            if cnt > 0:
                st = offsets[curr]
                stack.extend(sorted_srcs[st:st + cnt])

        return mask.reshape((self.rows, self.cols))


def delineate_catchment(
    flow_direction: np.ndarray,
    dem: np.ndarray,
    grid_x: np.ndarray,
    grid_y: np.ndarray,
    resolution: float,
    pond_x_m: float,
    pond_y_m: float,
    graph: Optional[UpstreamGraph] = None,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Traces upstream cells from the closest DEM cell to (pond_x_m, pond_y_m).
    Returns (catchment_mask, catchment_stats_dict).
    """
    if graph is None:
        graph = UpstreamGraph(flow_direction)

    dist_sq = (grid_x - pond_x_m) ** 2 + (grid_y - pond_y_m) ** 2
    pond_row, pond_col = np.unravel_index(np.argmin(dist_sq), dist_sq.shape)

    mask = graph.trace_upstream(int(pond_row), int(pond_col))

    cell_area = resolution * resolution
    catchment_cells = int(np.sum(mask))
    area_m2 = float(catchment_cells * cell_area)

    elev_vals = dem[mask]
    stats = {
        "cell_count": catchment_cells,
        "cell_area_m2": cell_area,
        "area_m2": area_m2,
        "area_hectares": area_m2 / 10_000.0,
        "min_elevation_m": float(elev_vals.min()) if catchment_cells > 0 else 0.0,
        "max_elevation_m": float(elev_vals.max()) if catchment_cells > 0 else 0.0,
        "mean_elevation_m": float(elev_vals.mean()) if catchment_cells > 0 else 0.0,
        "outlet_grid_row": int(pond_row),
        "outlet_grid_col": int(pond_col),
        "outlet_elevation_m": float(dem[pond_row, pond_col]),
    }

    return mask, stats


def delineate_custom_catchment(
    flow_direction: np.ndarray,
    dem: np.ndarray,
    grid_x: np.ndarray,
    grid_y: np.ndarray,
    resolution: float,
    epsg: int,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    x_m: Optional[float] = None,
    y_m: Optional[float] = None,
) -> Tuple[np.ndarray, Dict[str, Any], Dict[str, Any]]:
    """
    Delineates catchment for an arbitrary user-specified point (either WGS84 lat/lon or UTM x/y).
    Returns (mask, stats, geojson).
    """
    transformer_to_utm = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
    transformer_to_wgs84 = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)

    if x_m is None or y_m is None:
        if latitude is None or longitude is None:
            raise ValueError("Either (latitude, longitude) or (x_m, y_m) must be provided.")
        x_m, y_m = transformer_to_utm.transform(longitude, latitude)

    if latitude is None or longitude is None:
        lon, lat = transformer_to_wgs84.transform(x_m, y_m)
        longitude, latitude = float(lon), float(lat)

    mask, stats = delineate_catchment(
        flow_direction, dem, grid_x, grid_y, resolution, x_m, y_m
    )

    geojson = catchment_mask_to_geojson(
        mask, grid_x, grid_y, dem, resolution,
        float(x_m), float(y_m), epsg,
        stats, float(latitude), float(longitude)
    )

    return mask, stats, geojson


def catchment_mask_to_geojson(
    catchment_mask: np.ndarray,
    grid_x: np.ndarray,
    grid_y: np.ndarray,
    dem: np.ndarray,
    resolution: float,
    pond_x_m: float,
    pond_y_m: float,
    epsg: int,
    catchment_stats: Dict[str, Any],
    pond_lat: float,
    pond_lon: float,
    rank: Optional[int] = None,
    extra_properties: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Converts a catchment mask to a GeoJSON FeatureCollection with:
      - Catchment polygon (in WGS84)
      - Pond outlet point

    Uses horizontal run-length box merging for high speed polygonization.
    """
    rows, cols = catchment_mask.shape
    if not np.any(catchment_mask):
        raise ValueError("No catchment cells found in mask.")

    half = resolution / 2.0
    boxes = []

    # Fast row-run horizontal strip merging
    for r in range(rows):
        row_mask = catchment_mask[r]
        if not np.any(row_mask):
            continue
        diff = np.diff(np.pad(row_mask.astype(np.int8), (1, 1), 'constant'))
        starts = np.where(diff == 1)[0]
        ends = np.where(diff == -1)[0]
        for s, e in zip(starts, ends):
            x_min = float(grid_x[r, s]) - half
            x_max = float(grid_x[r, e - 1]) + half
            y_min = float(grid_y[r, s]) - half
            y_max = float(grid_y[r, s]) + half
            boxes.append(box(x_min, y_min, x_max, y_max))

    merged = unary_union(boxes).buffer(0)
    transformer = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)

    def _transform_ring(coords):
        xs = [pt[0] for pt in coords]
        ys = [pt[1] for pt in coords]
        lons, lats = transformer.transform(xs, ys)
        return [[float(lo), float(la)] for lo, la in zip(lons, lats)]

    def _poly_to_geojson_coords(poly):
        rings = [_transform_ring(poly.exterior.coords)]
        for interior in poly.interiors:
            rings.append(_transform_ring(interior.coords))
        return rings

    if merged.geom_type == "Polygon":
        geometry = {
            "type": "Polygon",
            "coordinates": _poly_to_geojson_coords(merged)
        }
    elif merged.geom_type == "MultiPolygon":
        geometry = {
            "type": "MultiPolygon",
            "coordinates": [_poly_to_geojson_coords(p) for p in merged.geoms]
        }
    else:
        polys = [p for p in merged.geoms if p.geom_type in ("Polygon", "MultiPolygon")]
        if polys:
            geometry = {
                "type": "MultiPolygon",
                "coordinates": [_poly_to_geojson_coords(p) for p in polys]
            }
        else:
            raise ValueError(f"Unexpected geometry type: {merged.geom_type}")

    dist_sq = (grid_x - pond_x_m) ** 2 + (grid_y - pond_y_m) ** 2
    outlet_r, outlet_c = np.unravel_index(np.argmin(dist_sq), grid_x.shape)
    outlet_elevation = float(dem[outlet_r, outlet_c])

    catchment_props = {
        "feature_type": "catchment",
        "rank": rank,
        "area_m2": catchment_stats["area_m2"],
        "area_hectares": catchment_stats["area_hectares"],
        "cell_count": catchment_stats["cell_count"],
        "min_elevation_m": catchment_stats["min_elevation_m"],
        "max_elevation_m": catchment_stats["max_elevation_m"],
        "mean_elevation_m": catchment_stats["mean_elevation_m"],
    }
    if extra_properties:
        catchment_props.update(extra_properties)

    pond_props = {
        "feature_type": "pond",
        "rank": rank,
        "elevation_m": outlet_elevation,
        "latitude": pond_lat,
        "longitude": pond_lon,
        "google_maps_url": f"https://www.google.com/maps?q={pond_lat},{pond_lon}",
    }
    if extra_properties:
        pond_props.update(extra_properties)

    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": catchment_props,
                "geometry": geometry,
            },
            {
                "type": "Feature",
                "properties": pond_props,
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(pond_lon), float(pond_lat)],
                },
            },
        ],
    }


def all_catchments_to_geojson(
    catchments_list: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Combines multiple catchment GeoJSON results into a single unified FeatureCollection.
    """
    all_features = []
    for item in catchments_list:
        geojson = item.get("geojson", {})
        features = geojson.get("features", [])
        all_features.extend(features)

    return {
        "type": "FeatureCollection",
        "features": all_features,
        "properties": {
            "total_catchments": len(catchments_list),
        }
    }
