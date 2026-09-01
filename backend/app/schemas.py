"""
Pydantic schemas for API request and response models.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


# ---------------------------------------------------------------------------
# Shared / sub-schemas
# ---------------------------------------------------------------------------

class CoordinateSystem(BaseModel):
    source: str = Field(description="Source CRS (e.g. EPSG:4326)")
    target: str = Field(description="Target UTM CRS (e.g. EPSG:32643)")
    projection: str = Field(description="Projection name")
    utm_zone: int = Field(description="UTM Zone number")
    hemisphere: str = Field(description="north or south")
    units: str = Field(description="Measurement units (meters)")


class PondCandidate(BaseModel):
    rank: int = Field(description="Rank from 1 (best) to N")
    latitude: float = Field(description="WGS84 Latitude")
    longitude: float = Field(description="WGS84 Longitude")
    x_m: float = Field(description="UTM Easting in meters")
    y_m: float = Field(description="UTM Northing in meters")
    elevation_m: float = Field(description="Elevation in meters")
    slope_degrees: float = Field(description="Slope in degrees")
    flow_accumulation_cells: float = Field(description="Number of upstream draining cells")
    suitability_score: float = Field(description="Combined MCE suitability score [0, 1]")
    google_maps_url: str = Field(description="Direct link to view site on Google Maps")


class CatchmentStats(BaseModel):
    cell_count: int = Field(description="Number of grid cells in catchment")
    cell_area_m2: float = Field(description="Area of a single cell in square meters")
    area_m2: float = Field(description="Total catchment area in square meters")
    area_hectares: float = Field(description="Catchment area in hectares")
    min_elevation_m: float = Field(description="Minimum elevation within catchment")
    max_elevation_m: float = Field(description="Maximum elevation within catchment")
    mean_elevation_m: float = Field(description="Mean elevation within catchment")
    outlet_grid_row: Optional[int] = None
    outlet_grid_col: Optional[int] = None
    outlet_elevation_m: Optional[float] = None


class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    properties: Dict[str, Any]
    geometry: Dict[str, Any]


class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[Dict[str, Any]]
    properties: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Terrain Schemas
# ---------------------------------------------------------------------------

class TerrainStats(BaseModel):
    min_m: float
    max_m: float
    mean_m: float
    std_m: float


class SlopeStats(BaseModel):
    min: float
    max: float
    mean: float
    std: Optional[float] = None


class TerrainClassification(BaseModel):
    flat_under_2deg_pct: float
    gentle_2_to_5deg_pct: float
    moderate_5_to_10deg_pct: float
    steep_over_10deg_pct: float


class TerrainAnalysisResponse(BaseModel):
    status: str
    elevation: TerrainStats
    slope_degrees: SlopeStats
    slope_percent: Dict[str, float]
    aspect_degrees: Dict[str, float]
    classification: TerrainClassification


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------

class CustomCatchmentRequest(BaseModel):
    latitude: Optional[float] = Field(default=None, description="WGS84 Latitude of custom point")
    longitude: Optional[float] = Field(default=None, description="WGS84 Longitude of custom point")
    x_m: Optional[float] = Field(default=None, description="UTM X coordinate in meters")
    y_m: Optional[float] = Field(default=None, description="UTM Y coordinate in meters")
    resolution_m: float = Field(default=1.0, gt=0, description="DEM resolution in meters")


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------

class ParseResponse(BaseModel):
    status: str
    contour_count: int
    sample: List[Dict[str, Any]]
    geojson: Optional[Dict[str, Any]] = None


class DemStats(BaseModel):
    shape: List[int]
    resolution_m: float
    min_elevation_m: float
    max_elevation_m: float
    mean_elevation_m: float
    coordinate_system: CoordinateSystem


class HydrologyStats(BaseModel):
    dem_shape: List[int]
    max_flow_accumulation: float
    mean_flow_accumulation: float
    cells_with_no_flow: int


class PondCandidatesResponse(BaseModel):
    status: str
    top_candidates_count: int
    min_separation_distance_m: float
    weights: Dict[str, float]
    candidates: List[PondCandidate]


class CatchmentResponse(BaseModel):
    status: str
    pond_rank: Optional[int] = None
    pond_outlet: Dict[str, Any]
    catchment: CatchmentStats
    geojson: Dict[str, Any]


class VisualizationResponse(BaseModel):
    status: str
    plot_type: str
    image_base64: str
    content_type: str = "image/png"


class StreamNetworkResponse(BaseModel):
    status: str
    threshold_percentile: float
    total_segments: int
    geojson: Dict[str, Any]


class FullPipelineResponse(BaseModel):
    status: str
    dem: DemStats
    hydrology: HydrologyStats
    terrain: Optional[Dict[str, Any]] = None
    candidates: List[PondCandidate]
    catchments: List[Dict[str, Any]]
    all_catchments_geojson: Optional[Dict[str, Any]] = None
    stream_network_geojson: Optional[Dict[str, Any]] = None
    contours_geojson: Optional[Dict[str, Any]] = None
    plots_base64: Optional[Dict[str, str]] = None
