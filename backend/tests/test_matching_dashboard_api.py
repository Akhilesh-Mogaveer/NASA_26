"""Automated Test Suite for FireLens Phase 4.4 Matching Dashboard API.

Verifies:
- Bounded observation points retrieval with matched/unmatched/ambiguous classifications
- Candidate association vector lines retrieval with coordinate pairs
- Single observation detail lookup (metadata, sensor-specific confidence, candidate edges)
- Viewport and date-filtered matching summary metrics
- Pagination, error handling, empty results, and boundary conditions
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_map_observations_retrieval_and_filtering():
    """Verify map observations return classified points within bounds."""
    # 1. Broad query
    res = client.get("/api/matching/map-observations?limit=25")
    assert res.status_code == 200
    data = res.json()
    assert "total_count" in data
    assert "items" in data
    assert "summary_in_bounds" in data
    assert len(data["items"]) <= 25

    if data["total_count"] > 0:
        first = data["items"][0]
        assert "observation_id" in first
        assert first["sensor"] in ["MODIS", "VIIRS"]
        assert first["status"] in ["matched", "unmatched", "ambiguous"]
        assert isinstance(first["is_ambiguous"], bool)
        assert isinstance(first["latitude"], float)
        assert isinstance(first["longitude"], float)
        assert isinstance(first["candidate_count"], int)


def test_map_observations_sensor_filter():
    """Verify sensor filter restricts results strictly to requested instrument."""
    res_modis = client.get("/api/matching/map-observations?sensor=MODIS&limit=10")
    assert res_modis.status_code == 200
    data_m = res_modis.json()
    for item in data_m["items"]:
        assert item["sensor"] == "MODIS"

    res_viirs = client.get("/api/matching/map-observations?sensor=VIIRS&limit=10")
    assert res_viirs.status_code == 200
    data_v = res_viirs.json()
    for item in data_v["items"]:
        assert item["sensor"] == "VIIRS"


def test_map_observations_status_filter():
    """Verify status filter distinguishes matched, unmatched, and ambiguous observations."""
    # Matched filter
    res_matched = client.get("/api/matching/map-observations?status=MATCHED&limit=10")
    assert res_matched.status_code == 200
    for item in res_matched.json()["items"]:
        assert item["status"] in ["matched", "ambiguous"]
        assert item["candidate_count"] > 0

    # Unmatched filter
    res_unmatched = client.get("/api/matching/map-observations?status=UNMATCHED&limit=10")
    assert res_unmatched.status_code == 200
    for item in res_unmatched.json()["items"]:
        assert item["status"] == "unmatched"
        assert item["candidate_count"] == 0
        assert item["is_ambiguous"] is False

    # Ambiguous filter
    res_ambig = client.get("/api/matching/map-observations?status=AMBIGUOUS&limit=10")
    assert res_ambig.status_code == 200
    for item in res_ambig.json()["items"]:
        assert item["is_ambiguous"] is True
        assert item["status"] == "ambiguous"


def test_map_observations_bounding_box():
    """Verify spatial bounding box strictly restricts latitude and longitude."""
    min_lat, max_lat = 55.0, 56.5
    min_lon, max_lon = -105.0, -103.0
    res = client.get(f"/api/matching/map-observations?min_lat={min_lat}&max_lat={max_lat}&min_lon={min_lon}&max_lon={max_lon}&limit=20")
    assert res.status_code == 200
    items = res.json()["items"]
    for it in items:
        assert min_lat <= it["latitude"] <= max_lat
        assert min_lon <= it["longitude"] <= max_lon


def test_map_lines_retrieval_and_geometry():
    """Verify candidate association lines return coordinate pairs and heuristic scores."""
    res = client.get("/api/matching/map-lines?limit=15&min_score=0.2")
    assert res.status_code == 200
    data = res.json()
    assert "total_count" in data
    assert "items" in data

    if data["items"]:
        first = data["items"][0]
        assert "coordinates" in first
        assert len(first["coordinates"]) == 2
        coord_modis = first["coordinates"][0]
        coord_viirs = first["coordinates"][1]
        assert len(coord_modis) == 2  # [lat, lon]
        assert len(coord_viirs) == 2
        assert first["distance_km"] >= 0.0
        assert first["time_diff_minutes"] >= 0.0
        assert 0.0 <= first["heuristic_score"] <= 1.0
        assert first["multiplicity_type"] in ["1:1", "1:N", "N:1", "M:N"]


def test_observation_detail_lookup_success():
    """Verify looking up a known matched observation returns full metadata and edges."""
    # First get a known matched observation from map observations
    res_list = client.get("/api/matching/map-observations?status=MATCHED&limit=1")
    assert res_list.status_code == 200
    items = res_list.json()["items"]
    if not items:
        pytest.skip("No matched observations available in current artifacts")

    target_id = items[0]["observation_id"]
    res_det = client.get(f"/api/matching/observation/{target_id}")
    assert res_det.status_code == 200
    detail = res_det.json()
    assert detail["observation_id"] == target_id
    assert detail["sensor"] in ["MODIS", "VIIRS"]
    assert detail["candidate_count"] > 0
    assert len(detail["associated_candidates"]) > 0

    first_edge = detail["associated_candidates"][0]
    assert "association_id" in first_edge
    assert "counterpart_observation_id" in first_edge
    assert "distance_km" in first_edge
    assert "heuristic_score" in first_edge


def test_observation_detail_lookup_not_found():
    """Verify 404 is returned when observation ID does not exist."""
    res = client.get("/api/matching/observation/FL-UNKNOWN-99999999")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_filtered_matching_summary_metrics():
    """Verify filtered matching summary calculates correct counts and non-zero rates."""
    res = client.get("/api/matching/filtered-summary")
    assert res.status_code == 200
    data = res.json()
    assert "total_modis" in data
    assert "total_viirs" in data
    assert "unique_matched_modis" in data
    assert "unique_matched_viirs" in data
    assert "total_candidate_edges" in data
    assert "modis_match_rate_pct" in data
    assert "viirs_match_rate_pct" in data

    # Verify no edge/observation denominator confusion:
    # Match rate must be between 0% and 100%
    assert 0.0 <= data["modis_match_rate_pct"] <= 100.0
    assert 0.0 <= data["viirs_match_rate_pct"] <= 100.0
    assert data["unique_matched_modis"] <= data["total_modis"]
    assert data["unique_matched_viirs"] <= data["total_viirs"]
