"""API Endpoint Tests for Phase 5.1 & Phase 5.2 Event Intelligence.

Tests FastAPI endpoints:
- GET /api/events/clustering/summary
- GET /api/events/clustering/clusters
- GET /api/events/clustering/{cluster_id}
- GET /api/events/clustering/{cluster_id}/observations
- GET /api/events/association/summary
- GET /api/events/association/relationships
- GET /api/events/association/{relationship_id}
- GET /api/events/map/clusters
- GET /api/events/map/relationships
- POST /api/events/clustering/run
- POST /api/events/association/run
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_api_clustering_summary():
    """Verify retrieval of clustering summary."""
    response = client.get("/api/events/clustering/summary")
    assert response.status_code == 200
    data = response.json()
    assert "modis" in data
    assert "viirs" in data
    assert "parameters" in data
    assert data["modis"]["cluster_count"] > 0
    assert data["viirs"]["cluster_count"] > 0


def test_api_clustering_clusters_listing():
    """Verify paginated cluster listing and sensor filtering."""
    # 1. All sensors
    res_all = client.get("/api/events/clustering/clusters?limit=10&offset=0")
    assert res_all.status_code == 200
    data_all = res_all.json()
    assert "items" in data_all
    assert len(data_all["items"]) <= 10
    assert data_all["total_count"] > 0

    # 2. Sensor = MODIS
    res_m = client.get("/api/events/clustering/clusters?sensor=MODIS&limit=10")
    assert res_m.status_code == 200
    data_m = res_m.json()
    for item in data_m["items"]:
        assert item["sensor"] == "MODIS"

    # 3. Sensor = VIIRS
    res_v = client.get("/api/events/clustering/clusters?sensor=VIIRS&limit=10")
    assert res_v.status_code == 200
    data_v = res_v.json()
    for item in data_v["items"]:
        assert item["sensor"] == "VIIRS"


def test_api_cluster_detail_lookup():
    """Verify looking up a specific cluster by ID."""
    # First get a cluster ID
    list_res = client.get("/api/events/clustering/clusters?limit=1")
    assert list_res.status_code == 200
    clusters = list_res.json()["items"]
    assert len(clusters) > 0
    cid = clusters[0]["cluster_id"]

    # Detail query
    detail_res = client.get(f"/api/events/clustering/{cid}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["cluster_id"] == cid
    assert "centroid_latitude" in detail
    assert "centroid_longitude" in detail
    assert "sum_frp_mw" in detail
    assert detail["observation_count"] >= 1


def test_api_cluster_observations_lookup():
    """Verify retrieving raw observations belonging to a cluster."""
    list_res = client.get("/api/events/clustering/clusters?limit=1")
    cid = list_res.json()["items"][0]["cluster_id"]

    obs_res = client.get(f"/api/events/clustering/{cid}/observations?limit=20")
    assert obs_res.status_code == 200
    data = obs_res.json()
    assert data["cluster_id"] == cid
    assert len(data["observations"]) > 0
    first_obs = data["observations"][0]
    assert "observation_id" in first_obs
    assert first_obs["cluster_id"] == cid


def test_api_cluster_not_found():
    """Verify 404 response for nonexistent cluster."""
    res = client.get("/api/events/clustering/CLUST-NONEXISTENT-99999")
    assert res.status_code == 404


def test_api_association_summary():
    """Verify retrieval of cross-sensor event association summary."""
    response = client.get("/api/events/association/summary")
    assert response.status_code == 200
    data = response.json()
    assert "modis_clusters_total" in data
    assert "viirs_clusters_total" in data
    assert "total_candidate_relationships" in data
    assert "multiplicity_breakdown" in data
    assert "classification_breakdown" in data
    assert data["total_candidate_relationships"] > 0


def test_api_event_relationships_listing():
    """Verify paginated relationship listing with multiplicity and score filters."""
    # 1. All relationships
    res = client.get("/api/events/association/relationships?limit=15&offset=0")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert len(data["items"]) <= 15
    assert data["total_count"] > 0

    first_rel = data["items"][0]
    assert "relationship_id" in first_rel
    assert "modis_cluster_id" in first_rel
    assert "viirs_cluster_id" in first_rel
    assert "heuristic_event_score" in first_rel
    assert "multiplicity_type" in first_rel

    # 2. Filter by multiplicity
    res_m = client.get("/api/events/association/relationships?multiplicity=1:1&limit=10")
    assert res_m.status_code == 200
    for item in res_m.json()["items"]:
        assert item["multiplicity_type"] == "1:1"


def test_api_event_relationship_detail():
    """Verify looking up a specific relationship by ID."""
    list_res = client.get("/api/events/association/relationships?limit=1")
    rel_id = list_res.json()["items"][0]["relationship_id"]

    detail_res = client.get(f"/api/events/association/{rel_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["relationship_id"] == rel_id
    assert detail["supporting_pairs_count"] >= 1
    assert "modis_centroid_lat" in detail
    assert "viirs_centroid_lat" in detail


def test_api_map_clusters():
    """Verify map clusters endpoint returns centroid objects."""
    res = client.get("/api/events/map/clusters?limit=50")
    assert res.status_code == 200
    data = res.json()
    assert "clusters" in data
    assert len(data["clusters"]) <= 50
    if len(data["clusters"]) > 0:
        c = data["clusters"][0]
        assert "latitude" in c
        assert "longitude" in c
        assert "sensor" in c
        assert "observation_count" in c


def test_api_map_relationships():
    """Verify map relationships endpoint returns vector line geometries."""
    res = client.get("/api/events/map/relationships?limit=50")
    assert res.status_code == 200
    data = res.json()
    assert "lines" in data
    assert len(data["lines"]) <= 50
    if len(data["lines"]) > 0:
        line = data["lines"][0]
        assert "coordinates" in line
        assert len(line["coordinates"]) == 2  # [[m_lat, m_lon], [v_lat, v_lon]]
        assert "heuristic_event_score" in line
        assert "multiplicity_type" in line
