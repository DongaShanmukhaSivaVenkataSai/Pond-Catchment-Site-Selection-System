"""
Main FastAPI Application
Pond Detection (PD) & Watershed Catchment Analysis Backend API
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import router

app = FastAPI(
    title="Pond Detection (PD) Backend API",
    description=(
        "High-performance REST API for farm-pond site selection, terrain modeling, "
        "and watershed catchment analysis.\n\n"
        "**Pipeline endpoints:**\n"
        "- `POST /api/v1/parse` — Parse KML contour file\n"
        "- `POST /api/v1/contours/geojson` — Export contours as WGS84 GeoJSON\n"
        "- `POST /api/v1/dem` — Build Digital Elevation Model (DEM)\n"
        "- `POST /api/v1/terrain` — Detailed terrain slope & aspect analysis\n"
        "- `POST /api/v1/hydrology` — D8 flow direction & accumulation\n"
        "- `POST /api/v1/streams/geojson` — Extract drainage stream network GeoJSON\n"
        "- `POST /api/v1/pond-candidates` — MCE pond site scoring & Spatial NMS\n"
        "- `POST /api/v1/catchment` — Delineate catchment for ranked pond\n"
        "- `POST /api/v1/catchment/custom` — Delineate catchment for custom (lat, lon) or (x, y)\n"
        "- `POST /api/v1/catchments/all` — Delineate all top-N catchments (unified GeoJSON)\n"
        "- `POST /api/v1/visualize/{plot_type}` — Generate map plots (PNG or Base64)\n"
        "- `POST /api/v1/export/csv` — Download candidate and catchment summary CSV\n"
        "- `POST /api/v1/analyze` — **Full End-to-End Pipeline** in a single call\n"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(router)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": "Pond Detection (PD) Backend API",
        "version": "1.0.0",
        "status": "online",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "health": "GET /api/v1/health",
            "parse_kml": "POST /api/v1/parse",
            "contours_geojson": "POST /api/v1/contours/geojson",
            "build_dem": "POST /api/v1/dem",
            "terrain_analysis": "POST /api/v1/terrain",
            "hydrology": "POST /api/v1/hydrology",
            "streams_geojson": "POST /api/v1/streams/geojson",
            "pond_candidates": "POST /api/v1/pond-candidates",
            "catchment": "POST /api/v1/catchment",
            "custom_catchment": "POST /api/v1/catchment/custom",
            "all_catchments": "POST /api/v1/catchments/all",
            "visualize": "POST /api/v1/visualize/{plot_type}",
            "export_csv": "POST /api/v1/export/csv",
            "full_pipeline": "POST /api/v1/analyze",
        },
    }
