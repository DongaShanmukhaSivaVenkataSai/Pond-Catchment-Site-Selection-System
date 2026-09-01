"""
Integration tests for FastAPI REST API endpoints.
"""

import os
import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

KML_PATH = os.path.join(os.path.dirname(__file__), "..", "contours_1m.kml")


def test_health():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"


def test_parse_kml_endpoint():
    with open(KML_PATH, "rb") as f:
        res = client.post("/api/v1/parse", files={"file": ("contours_1m.kml", f, "application/vnd.google-earth.kml+xml")})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["contour_count"] > 1000


def test_contours_geojson_endpoint():
    with open(KML_PATH, "rb") as f:
        res = client.post("/api/v1/contours/geojson", files={"file": ("contours_1m.kml", f, "application/vnd.google-earth.kml+xml")})
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) > 1000


def test_dem_endpoint():
    with open(KML_PATH, "rb") as f:
        res = client.post("/api/v1/dem?resolution_m=2.0", files={"file": ("contours_1m.kml", f, "application/vnd.google-earth.kml+xml")})
    assert res.status_code == 200
    data = res.json()
    assert "shape" in data
    assert data["resolution_m"] == 2.0
    assert data["min_elevation_m"] > 0


def test_terrain_endpoint():
    with open(KML_PATH, "rb") as f:
        res = client.post("/api/v1/terrain?resolution_m=2.0", files={"file": ("contours_1m.kml", f, "application/vnd.google-earth.kml+xml")})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "slope_degrees" in data
    assert "classification" in data


def test_hydrology_endpoint():
    with open(KML_PATH, "rb") as f:
        res = client.post("/api/v1/hydrology?resolution_m=2.0", files={"file": ("contours_1m.kml", f, "application/vnd.google-earth.kml+xml")})
    assert res.status_code == 200
    data = res.json()
    assert "max_flow_accumulation" in data
    assert data["max_flow_accumulation"] > 1.0


def test_streams_geojson_endpoint():
    with open(KML_PATH, "rb") as f:
        res = client.post("/api/v1/streams/geojson?resolution_m=2.0&threshold_percentile=99.0", files={"file": ("contours_1m.kml", f, "application/vnd.google-earth.kml+xml")})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["geojson"]["type"] == "FeatureCollection"


def test_pond_candidates_endpoint():
    with open(KML_PATH, "rb") as f:
        res = client.post("/api/v1/pond-candidates?resolution_m=2.0&top_n=3", files={"file": ("contours_1m.kml", f, "application/vnd.google-earth.kml+xml")})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert len(data["candidates"]) == 3
    assert data["candidates"][0]["rank"] == 1


def test_catchment_endpoint():
    with open(KML_PATH, "rb") as f:
        res = client.post("/api/v1/catchment?resolution_m=2.0&pond_rank=1", files={"file": ("contours_1m.kml", f, "application/vnd.google-earth.kml+xml")})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["pond_rank"] == 1
    assert "catchment" in data
    assert data["geojson"]["type"] == "FeatureCollection"


def test_custom_catchment_endpoint():
    with open(KML_PATH, "rb") as f:
        res = client.post(
            "/api/v1/catchment/custom?latitude=21.25&longitude=81.30&resolution_m=2.0",
            files={"file": ("contours_1m.kml", f, "application/vnd.google-earth.kml+xml")}
        )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["geojson"]["type"] == "FeatureCollection"


def test_all_catchments_endpoint():
    with open(KML_PATH, "rb") as f:
        res = client.post("/api/v1/catchments/all?resolution_m=2.0&top_n=3", files={"file": ("contours_1m.kml", f, "application/vnd.google-earth.kml+xml")})
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) > 0


def test_visualize_endpoint():
    with open(KML_PATH, "rb") as f:
        res = client.post(
            "/api/v1/visualize/dem?resolution_m=2.0&format=json",
            files={"file": ("contours_1m.kml", f, "application/vnd.google-earth.kml+xml")}
        )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["image_base64"].startswith("data:image/png;base64,")


def test_csv_export_endpoint():
    with open(KML_PATH, "rb") as f:
        res = client.post(
            "/api/v1/export/csv?resolution_m=2.0&top_n=3",
            files={"file": ("contours_1m.kml", f, "application/vnd.google-earth.kml+xml")}
        )
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "Rank,Latitude,Longitude" in res.text


def test_full_pipeline_endpoint():
    with open(KML_PATH, "rb") as f:
        res = client.post(
            "/api/v1/analyze?resolution_m=2.0&top_n=2&include_plots=false",
            files={"file": ("contours_1m.kml", f, "application/vnd.google-earth.kml+xml")}
        )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert len(data["candidates"]) == 2
    assert len(data["catchments"]) == 2
    assert "all_catchments_geojson" in data

