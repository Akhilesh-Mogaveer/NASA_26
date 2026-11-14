"""Unit tests for FireLens Analytics services and API endpoints."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.analytics import (
    get_analytics_overview,
    get_temporal_analytics,
    get_frp_analytics,
    get_sensor_comparison_analytics,
    get_geographical_analytics,
    get_grid_density_data,
    clear_analytics_cache,
)

client = TestClient(app)


def test_analytics_overview_service():
    """Verify overview service loads authentic metadata and counts."""
    data = get_analytics_overview()
    assert "counts" in data
    assert data["counts"]["total_observations"] > 0
    assert data["counts"]["modis_count"] > 0
    assert data["counts"]["viirs_count"] > 0
    assert data["counts"]["viirs_to_modis_ratio"] > 4.0
    assert "energetics" in data
    assert "frp_aggregates" in data
    assert data["frp_aggregates"]["total_frp_mw"] > 0
    assert len(data["key_findings"]) >= 3


def test_temporal_analytics_service():
    """Verify temporal service returns monthly, hourly, and day/night stats."""
    data = get_temporal_analytics()
    assert "monthly" in data
    assert len(data["monthly"]) == 12  # All 12 months of 2025
    assert "hourly" in data
    assert len(data["hourly"]) == 24   # 0 to 23 UTC
    assert "day_night" in data
    assert "modis" in data["day_night"]
    assert "viirs" in data["day_night"]
    assert data["day_night"]["modis"]["day_percentage"] > 50


def test_frp_analytics_service():
    """Verify FRP metrics and log-binned histogram."""
    data = get_frp_analytics()
    assert "overall" in data
    assert "modis" in data
    assert "viirs" in data
    assert data["modis"]["mean"] > data["viirs"]["mean"]  # MODIS mean higher due to 1km resolution
    assert "histogram" in data
    assert len(data["histogram"]) >= 5


def test_sensor_comparison_service():
    """Verify sensor comparison service."""
    data = get_sensor_comparison_analytics()
    assert "observations" in data
    assert "spatial_resolution" in data
    assert data["spatial_resolution"]["modis_nadir_resolution_m"] == 1000
    assert data["spatial_resolution"]["viirs_nadir_resolution_m"] == 375
    assert len(data["scientific_reasons_for_divergence"]) >= 3


def test_geographical_analytics_service():
    """Verify 2-degree cell and latitudinal distribution."""
    data = get_geographical_analytics(top_n=10)
    assert data["total_active_cells"] > 0
    assert len(data["top_cells"]) <= 10
    assert len(data["latitudinal_distribution"]) > 10


def test_grid_density_service():
    """Verify grid density filtering and pagination."""
    cells = get_grid_density_data(min_count=100, limit=20)
    assert len(cells) <= 20
    for cell in cells:
        assert cell["total_count"] >= 100


def test_api_analytics_overview():
    """Test GET /api/analytics/overview."""
    response = client.get("/api/analytics/overview")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["counts"]["total_observations"] == 22175341
    assert "NASA FIRMS" in json_data["dataset_provenance"]


def test_api_analytics_temporal():
    """Test GET /api/analytics/temporal."""
    response = client.get("/api/analytics/temporal")
    assert response.status_code == 200
    json_data = response.json()
    assert len(json_data["monthly"]) == 12
    assert len(json_data["hourly"]) == 24


def test_api_analytics_frp():
    """Test GET /api/analytics/frp."""
    response = client.get("/api/analytics/frp")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["modis"]["mean"] == 41.21
    assert json_data["viirs"]["mean"] == 9.68


def test_api_analytics_sensor_comparison():
    """Test GET /api/analytics/sensor-comparison."""
    response = client.get("/api/analytics/sensor-comparison")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["observations"]["viirs_to_modis_ratio"] == 4.979


def test_api_analytics_geographical():
    """Test GET /api/analytics/geographical."""
    response = client.get("/api/analytics/geographical?top_n=5")
    assert response.status_code == 200
    json_data = response.json()
    assert len(json_data["top_cells"]) == 5


def test_api_analytics_grid_density():
    """Test GET /api/analytics/grid-density."""
    response = client.get("/api/analytics/grid-density?min_count=500&limit=50")
    assert response.status_code == 200
    json_data = response.json()
    assert isinstance(json_data, list)
    assert len(json_data) <= 50
    if json_data:
        assert json_data[0]["total_count"] >= 500


def test_cache_clearing():
    """Test cache clearing mechanism."""
    clear_analytics_cache()
    data = get_analytics_overview()
    assert data is not None
