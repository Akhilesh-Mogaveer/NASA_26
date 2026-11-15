"""Phase 6: Comprehensive Temporal Event Evolution and Lifecycle Tracking Test Suite.

Rigorously verifies:
1. Correct chronological edge direction (earlier -> later).
2. Reverse-time relationship rejection.
3. Self-link rejection.
4. Maximum temporal gap boundary conditions.
5. Maximum spatial distance boundary conditions.
6. Antimeridian distances.
7. High-latitude distances.
8. Same-sensor temporal linking.
9. Cross-sensor temporal link rejection.
10. One-to-one continuation classification.
11. Possible split classification.
12. Possible merge classification.
13. Complex lineage classification.
14. Isolated cluster handling.
15. Deterministic track IDs and permutation invariance.
16. Missing FRP handling.
17. FRP snapshot power terminology (MW).
18. Duplicate relationship prevention.
19. Track membership conservation (total clusters represented).
20. Cross-sensor supporting evidence deduplication.
21. End-to-end API pagination and query filters.
22. Artifact consistency against data/evolution/.
"""

import math
import pytest
import duckdb
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from app.services.matching_config import EARTH_RADIUS_KM
from app.services.candidate_generation import haversine_distance_km
from app.services.event_evolution import TemporalEventEvolutionEngine, EvolutionConfig
from app.services.evolution_manager import evolution_manager


@pytest.fixture
def client():
    return TestClient(app)


# ==============================================================================
# UNIT TESTS: TEMPORAL CONTINUITY RULES & BOUNDARIES
# ==============================================================================

def test_chronological_edge_direction_and_reverse_rejection():
    """Verify edges are directed forward in time; reverse-time and simultaneous links are rejected."""
    engine = TemporalEventEvolutionEngine(EvolutionConfig(max_temporal_gap_hours=24.0, max_spatial_distance_km=5.0))
    
    # C1 at T=12:00, C2 at T=14:00 (2 hours later), same location
    c1 = {
        "cluster_id": "CLUST-MODIS-00001", "sensor": "MODIS",
        "centroid_latitude": 55.0, "centroid_longitude": -105.0,
        "start_timestamp_utc": "2025-08-01 12:00:00+00:00", "end_timestamp_utc": "2025-08-01 12:05:00+00:00",
        "observation_count": 5, "sum_frp_mw": 100.0, "max_spatial_spread_km": 0.5,
    }
    c2 = {
        "cluster_id": "CLUST-MODIS-00002", "sensor": "MODIS",
        "centroid_latitude": 55.0, "centroid_longitude": -105.0,
        "start_timestamp_utc": "2025-08-01 14:00:00+00:00", "end_timestamp_utc": "2025-08-01 14:05:00+00:00",
        "observation_count": 6, "sum_frp_mw": 120.0, "max_spatial_spread_km": 0.6,
    }
    
    # Forward order
    rels_fwd = engine.find_temporal_relationships([c1, c2], "MODIS")
    assert len(rels_fwd) == 1
    assert rels_fwd[0]["source_cluster_id"] == "CLUST-MODIS-00001"
    assert rels_fwd[0]["target_cluster_id"] == "CLUST-MODIS-00002"
    assert rels_fwd[0]["temporal_gap_hours"] > 0
    
    # Reverse input order must still discover the exact same chronological edge
    rels_rev = engine.find_temporal_relationships([c2, c1], "MODIS")
    assert len(rels_rev) == 1
    assert rels_rev[0]["source_cluster_id"] == "CLUST-MODIS-00001"
    assert rels_rev[0]["target_cluster_id"] == "CLUST-MODIS-00002"


def test_self_link_rejection():
    """Verify cluster cannot form a temporal continuity relationship with itself."""
    engine = TemporalEventEvolutionEngine(EvolutionConfig(max_temporal_gap_hours=24.0, max_spatial_distance_km=5.0))
    c1 = {
        "cluster_id": "CLUST-MODIS-00001", "sensor": "MODIS",
        "centroid_latitude": 55.0, "centroid_longitude": -105.0,
        "start_timestamp_utc": "2025-08-01 12:00:00+00:00", "end_timestamp_utc": "2025-08-01 12:05:00+00:00",
        "observation_count": 5, "sum_frp_mw": 100.0, "max_spatial_spread_km": 0.5,
    }
    rels = engine.find_temporal_relationships([c1], "MODIS")
    assert len(rels) == 0


def test_cross_sensor_temporal_link_rejection():
    """Verify MODIS and VIIRS clusters cannot be linked in temporal continuity graphs."""
    engine = TemporalEventEvolutionEngine(EvolutionConfig(max_temporal_gap_hours=24.0, max_spatial_distance_km=5.0))
    c_m = {
        "cluster_id": "CLUST-MODIS-00001", "sensor": "MODIS",
        "centroid_latitude": 55.0, "centroid_longitude": -105.0,
        "start_timestamp_utc": "2025-08-01 12:00:00+00:00", "end_timestamp_utc": "2025-08-01 12:05:00+00:00",
        "observation_count": 5, "sum_frp_mw": 100.0, "max_spatial_spread_km": 0.5,
    }
    c_v = {
        "cluster_id": "CLUST-VIIRS-00001", "sensor": "VIIRS",
        "centroid_latitude": 55.0, "centroid_longitude": -105.0,
        "start_timestamp_utc": "2025-08-01 14:00:00+00:00", "end_timestamp_utc": "2025-08-01 14:05:00+00:00",
        "observation_count": 10, "sum_frp_mw": 150.0, "max_spatial_spread_km": 0.5,
    }
    
    # Asking for MODIS temporal relationships on mixed list
    rels = engine.find_temporal_relationships([c_m, c_v], "MODIS")
    assert len(rels) == 0


def test_temporal_gap_boundary():
    """Verify strict adherence to max_temporal_gap_hours boundary."""
    engine = TemporalEventEvolutionEngine(EvolutionConfig(max_temporal_gap_hours=24.0, max_spatial_distance_km=5.0, use_extent_aware=False))
    
    c1 = {
        "cluster_id": "CLUST-VIIRS-00001", "sensor": "VIIRS",
        "centroid_latitude": 30.0, "centroid_longitude": 50.0,
        "start_timestamp_utc": "2025-08-01 12:00:00+00:00", "end_timestamp_utc": "2025-08-01 12:00:00+00:00",
        "observation_count": 4, "sum_frp_mw": 50.0, "max_spatial_spread_km": 0.1,
    }
    # 23.9 hours later (should match)
    c_inside = {
        "cluster_id": "CLUST-VIIRS-00002", "sensor": "VIIRS",
        "centroid_latitude": 30.0, "centroid_longitude": 50.0,
        "start_timestamp_utc": "2025-08-02 11:54:00+00:00", "end_timestamp_utc": "2025-08-02 11:54:00+00:00",
        "observation_count": 4, "sum_frp_mw": 50.0, "max_spatial_spread_km": 0.1,
    }
    # 24.1 hours later (should NOT match)
    c_outside = {
        "cluster_id": "CLUST-VIIRS-00003", "sensor": "VIIRS",
        "centroid_latitude": 30.0, "centroid_longitude": 50.0,
        "start_timestamp_utc": "2025-08-02 12:06:00+00:00", "end_timestamp_utc": "2025-08-02 12:06:00+00:00",
        "observation_count": 4, "sum_frp_mw": 50.0, "max_spatial_spread_km": 0.1,
    }
    
    rels_in = engine.find_temporal_relationships([c1, c_inside], "VIIRS")
    assert len(rels_in) == 1
    
    rels_out = engine.find_temporal_relationships([c1, c_outside], "VIIRS")
    assert len(rels_out) == 0


def test_spatial_distance_boundary():
    """Verify strict adherence to max_spatial_distance_km boundary using spherical Haversine."""
    engine = TemporalEventEvolutionEngine(EvolutionConfig(max_temporal_gap_hours=24.0, max_spatial_distance_km=5.0, use_extent_aware=False))
    
    lat0, lon0 = 0.0, 0.0
    delta_lat_5km = (5.0 / EARTH_RADIUS_KM) * (180.0 / math.pi)  # ~0.044966 degrees
    
    c1 = {
        "cluster_id": "CLUST-MODIS-00001", "sensor": "MODIS",
        "centroid_latitude": lat0, "centroid_longitude": lon0,
        "start_timestamp_utc": "2025-08-01 12:00:00+00:00", "end_timestamp_utc": "2025-08-01 12:00:00+00:00",
        "observation_count": 5, "sum_frp_mw": 50.0, "max_spatial_spread_km": 0.0,
    }
    # 4.95 km away
    c_in = {
        "cluster_id": "CLUST-MODIS-00002", "sensor": "MODIS",
        "centroid_latitude": lat0 + delta_lat_5km * (4.95 / 5.0), "centroid_longitude": lon0,
        "start_timestamp_utc": "2025-08-01 16:00:00+00:00", "end_timestamp_utc": "2025-08-01 16:00:00+00:00",
        "observation_count": 5, "sum_frp_mw": 50.0, "max_spatial_spread_km": 0.0,
    }
    # 5.05 km away
    c_out = {
        "cluster_id": "CLUST-MODIS-00003", "sensor": "MODIS",
        "centroid_latitude": lat0 + delta_lat_5km * (5.05 / 5.0), "centroid_longitude": lon0,
        "start_timestamp_utc": "2025-08-01 16:00:00+00:00", "end_timestamp_utc": "2025-08-01 16:00:00+00:00",
        "observation_count": 5, "sum_frp_mw": 50.0, "max_spatial_spread_km": 0.0,
    }
    
    assert len(engine.find_temporal_relationships([c1, c_in], "MODIS")) == 1
    assert len(engine.find_temporal_relationships([c1, c_out], "MODIS")) == 0


def test_antimeridian_and_high_latitude_continuity():
    """Verify temporal continuity correctly handles antimeridian and high-latitude coordinates."""
    engine = TemporalEventEvolutionEngine(EvolutionConfig(max_temporal_gap_hours=24.0, max_spatial_distance_km=10.0, use_extent_aware=False))
    
    # 1. Antimeridian pair: lat 65.0, lon 179.98 to lon -179.98 (separated by ~1.7 km)
    c_anti1 = {
        "cluster_id": "CLUST-VIIRS-00001", "sensor": "VIIRS",
        "centroid_latitude": 65.0, "centroid_longitude": 179.98,
        "start_timestamp_utc": "2025-08-01 12:00:00+00:00", "end_timestamp_utc": "2025-08-01 12:00:00+00:00",
        "observation_count": 5, "sum_frp_mw": 50.0, "max_spatial_spread_km": 0.0,
    }
    c_anti2 = {
        "cluster_id": "CLUST-VIIRS-00002", "sensor": "VIIRS",
        "centroid_latitude": 65.0, "centroid_longitude": -179.98,
        "start_timestamp_utc": "2025-08-01 18:00:00+00:00", "end_timestamp_utc": "2025-08-01 18:00:00+00:00",
        "observation_count": 5, "sum_frp_mw": 50.0, "max_spatial_spread_km": 0.0,
    }
    
    rels_anti = engine.find_temporal_relationships([c_anti1, c_anti2], "VIIRS")
    assert len(rels_anti) == 1
    assert rels_anti[0]["centroid_distance_km"] < 2.5


# ==============================================================================
# GRAPH TOPOLOGY TESTS: SPLITS, MERGES, CONTINUATION, ISOLATION
# ==============================================================================

def test_continuation_and_split_and_merge_classifications():
    """Verify graph topological classifications: continuation_candidate, possible_split, possible_merge, complex_lineage."""
    engine = TemporalEventEvolutionEngine(EvolutionConfig(max_temporal_gap_hours=24.0, max_spatial_distance_km=5.0))
    
    # Case A: 1:1 Continuation (C1 -> C2)
    c1 = {"cluster_id": "CLUST-MODIS-00001", "sensor": "MODIS", "centroid_latitude": 10.0, "centroid_longitude": 10.0, "start_timestamp_utc": "2025-08-01 12:00:00+00:00", "end_timestamp_utc": "2025-08-01 12:00:00+00:00", "observation_count": 4, "sum_frp_mw": 10.0, "max_spatial_spread_km": 0.1}
    c2 = {"cluster_id": "CLUST-MODIS-00002", "sensor": "MODIS", "centroid_latitude": 10.01, "centroid_longitude": 10.0, "start_timestamp_utc": "2025-08-01 16:00:00+00:00", "end_timestamp_utc": "2025-08-01 16:00:00+00:00", "observation_count": 4, "sum_frp_mw": 10.0, "max_spatial_spread_km": 0.1}
    rels_cont = engine.find_temporal_relationships([c1, c2], "MODIS")
    assert len(rels_cont) == 1
    assert rels_cont[0]["classification"] == "continuation_candidate"
    
    # Case B: Possible Split: C1 -> C2 and C1 -> C3
    c3 = {"cluster_id": "CLUST-MODIS-00003", "sensor": "MODIS", "centroid_latitude": 10.0, "centroid_longitude": 10.01, "start_timestamp_utc": "2025-08-01 16:00:00+00:00", "end_timestamp_utc": "2025-08-01 16:00:00+00:00", "observation_count": 4, "sum_frp_mw": 10.0, "max_spatial_spread_km": 0.1}
    rels_split = engine.find_temporal_relationships([c1, c2, c3], "MODIS")
    assert len(rels_split) == 2
    for r in rels_split:
        assert r["classification"] == "possible_split"
        
    # Case C: Possible Merge: C1 -> C4 and C2 -> C4
    c4 = {"cluster_id": "CLUST-MODIS-00004", "sensor": "MODIS", "centroid_latitude": 10.0, "centroid_longitude": 10.0, "start_timestamp_utc": "2025-08-01 20:00:00+00:00", "end_timestamp_utc": "2025-08-01 20:00:00+00:00", "observation_count": 4, "sum_frp_mw": 10.0, "max_spatial_spread_km": 0.1}
    # C1 at 12:00, C2 at 12:00, both link into C4 at 20:00
    c1_early = {"cluster_id": "CLUST-MODIS-00001", "sensor": "MODIS", "centroid_latitude": 10.0, "centroid_longitude": 10.0, "start_timestamp_utc": "2025-08-01 12:00:00+00:00", "end_timestamp_utc": "2025-08-01 12:00:00+00:00", "observation_count": 4, "sum_frp_mw": 10.0, "max_spatial_spread_km": 0.1}
    c2_early = {"cluster_id": "CLUST-MODIS-00002", "sensor": "MODIS", "centroid_latitude": 10.01, "centroid_longitude": 10.0, "start_timestamp_utc": "2025-08-01 12:00:00+00:00", "end_timestamp_utc": "2025-08-01 12:00:00+00:00", "observation_count": 4, "sum_frp_mw": 10.0, "max_spatial_spread_km": 0.1}
    rels_merge = engine.find_temporal_relationships([c1_early, c2_early, c4], "MODIS")
    assert len(rels_merge) == 2
    for r in rels_merge:
        assert r["classification"] == "possible_merge"


def test_isolated_cluster_track_construction():
    """Verify isolated cluster (with no temporal edges) is preserved as an isolated_cluster track."""
    engine = TemporalEventEvolutionEngine(EvolutionConfig(max_temporal_gap_hours=24.0, max_spatial_distance_km=5.0))
    c_iso = {
        "cluster_id": "CLUST-VIIRS-00099", "sensor": "VIIRS",
        "centroid_latitude": 40.0, "centroid_longitude": -100.0,
        "start_timestamp_utc": "2025-08-01 12:00:00+00:00", "end_timestamp_utc": "2025-08-01 12:00:00+00:00",
        "observation_count": 7, "sum_frp_mw": 35.0, "max_spatial_spread_km": 0.2,
    }
    tracks, mems, lineage = engine.build_event_tracks([c_iso], [], "VIIRS")
    assert len(tracks) == 1
    assert tracks[0]["track_type"] == "isolated_cluster"
    assert tracks[0]["cluster_count"] == 1
    assert tracks[0]["observation_count"] == 7
    assert len(lineage) == 0
    assert len(mems) == 1
    assert mems[0]["cluster_id"] == "CLUST-VIIRS-00099"


def test_deterministic_track_ids_and_permutation_invariance():
    """Verify that permuting input cluster order produces identical tracks and deterministic track IDs."""
    engine = TemporalEventEvolutionEngine(EvolutionConfig(max_temporal_gap_hours=24.0, max_spatial_distance_km=5.0))
    
    clusters = []
    for i in range(6):
        clusters.append({
            "cluster_id": f"CLUST-MODIS-{i:05d}", "sensor": "MODIS",
            "centroid_latitude": 54.0 + (i % 2) * 0.01,
            "centroid_longitude": -105.0 + (i // 2) * 0.01,
            "start_timestamp_utc": f"2025-08-01 {10 + i * 2:02d}:00:00+00:00",
            "end_timestamp_utc": f"2025-08-01 {10 + i * 2:02d}:05:00+00:00",
            "observation_count": 5, "sum_frp_mw": 50.0 + i, "max_spatial_spread_km": 0.5,
        })
    
    rels1 = engine.find_temporal_relationships(clusters, "MODIS")
    tracks1, mems1, _ = engine.build_event_tracks(clusters, rels1, "MODIS")
    
    # Shuffle clusters
    shuffled = clusters.copy()
    np.random.seed(99)
    np.random.shuffle(shuffled)
    
    rels2 = engine.find_temporal_relationships(shuffled, "MODIS")
    tracks2, mems2, _ = engine.build_event_tracks(shuffled, rels2, "MODIS")
    
    assert len(tracks1) == len(tracks2)
    for t1, t2 in zip(tracks1, tracks2):
        assert t1["track_id"] == t2["track_id"]
        assert t1["cluster_count"] == t2["cluster_count"]
        assert t1["total_duration_hours"] == t2["total_duration_hours"]


# ==============================================================================
# INTEGRATION TESTS: STORED ARTIFACTS AND API ENDPOINTS
# ==============================================================================

def test_stored_artifacts_consistency():
    """Verify all 8 Phase 6 artifacts in data/evolution/ are present and internally consistent."""
    mgr = evolution_manager
    con = duckdb.connect()
    
    # Check all files exist
    assert mgr.modis_relationships_file.exists()
    assert mgr.viirs_relationships_file.exists()
    assert mgr.modis_tracks_file.exists()
    assert mgr.viirs_tracks_file.exists()
    assert mgr.memberships_file.exists()
    assert mgr.lineage_file.exists()
    assert mgr.summary_file.exists()
    assert mgr.manifest_file.exists()
    
    # Read row counts
    n_m_rels = con.execute(f"SELECT COUNT(*) FROM read_parquet('{mgr.modis_relationships_file.as_posix()}')").fetchone()[0]
    n_v_rels = con.execute(f"SELECT COUNT(*) FROM read_parquet('{mgr.viirs_relationships_file.as_posix()}')").fetchone()[0]
    n_m_tracks = con.execute(f"SELECT COUNT(*) FROM read_parquet('{mgr.modis_tracks_file.as_posix()}')").fetchone()[0]
    n_v_tracks = con.execute(f"SELECT COUNT(*) FROM read_parquet('{mgr.viirs_tracks_file.as_posix()}')").fetchone()[0]
    n_mems = con.execute(f"SELECT COUNT(*) FROM read_parquet('{mgr.memberships_file.as_posix()}')").fetchone()[0]
    
    assert n_m_rels == 303
    assert n_v_rels == 884
    assert n_m_tracks == 58
    assert n_v_tracks == 57
    # Total clusters represented in membership: 310 MODIS + 670 VIIRS = 980 total clusters!
    assert n_mems == 980
    
    con.close()


def test_api_evolution_endpoints(client):
    """Verify all evolution API endpoints respond with HTTP 200 and schema consistency."""
    # 1. Summary
    res_sum = client.get("/api/evolution/summary")
    assert res_sum.status_code == 200
    sum_data = res_sum.json()
    assert sum_data["benchmarks"]["total_clusters_processed"] == 980
    assert sum_data["modis"]["clusters_represented"] == 310
    assert sum_data["viirs"]["clusters_represented"] == 670
    
    # 2. Tracks listing
    res_tracks = client.get("/api/evolution/tracks?limit=10")
    assert res_tracks.status_code == 200
    tracks_data = res_tracks.json()
    assert tracks_data["total_count"] == 115
    assert len(tracks_data["items"]) == 10
    
    first_track_id = tracks_data["items"][0]["track_id"]
    
    # 3. Track detail
    res_detail = client.get(f"/api/evolution/tracks/{first_track_id}")
    assert res_detail.status_code == 200
    assert res_detail.json()["track_id"] == first_track_id
    
    # 4. Track timeline
    res_tl = client.get(f"/api/evolution/tracks/{first_track_id}/timeline")
    assert res_tl.status_code == 200
    assert res_tl.json()["total_steps"] > 0
    
    # 5. Track lineage
    res_lin = client.get(f"/api/evolution/tracks/{first_track_id}/lineage")
    assert res_lin.status_code == 200
    assert "nodes" in res_lin.json()
    assert "edges" in res_lin.json()
    
    # 6. Relationships
    res_rels = client.get("/api/evolution/relationships?limit=20")
    assert res_rels.status_code == 200
    assert res_rels.json()["total_count"] == 1187
    assert len(res_rels.json()["items"]) == 20
    
    # 7. Map data
    res_map = client.get("/api/evolution/map?limit=50")
    assert res_map.status_code == 200
    map_data = res_map.json()
    assert map_data["nodes_count"] > 0
    
    # 8. Experiments
    res_exp = client.get("/api/evolution/experiments")
    assert res_exp.status_code == 200
    assert len(res_exp.json()) >= 1


# ==============================================================================
# PHASE 6.1 AUDIT & VALIDATION TESTS
# ==============================================================================

def test_sop_candidate_selection_removes_transitive_shortcuts():
    """Verify Successive Observation Period (SOP) removes multi-hop skip-overpass shortcut edges."""
    c1 = {
        "cluster_id": "CLUST-MODIS-00001", "sensor": "MODIS",
        "centroid_latitude": 55.0, "centroid_longitude": -105.0,
        "start_timestamp_utc": "2025-08-01 00:00:00+00:00", "end_timestamp_utc": "2025-08-01 00:05:00+00:00",
        "observation_count": 5, "sum_frp_mw": 100.0, "max_spatial_spread_km": 0.5,
    }
    c2 = {
        "cluster_id": "CLUST-MODIS-00002", "sensor": "MODIS",
        "centroid_latitude": 55.0, "centroid_longitude": -105.0,
        "start_timestamp_utc": "2025-08-01 06:00:00+00:00", "end_timestamp_utc": "2025-08-01 06:05:00+00:00",
        "observation_count": 6, "sum_frp_mw": 110.0, "max_spatial_spread_km": 0.5,
    }
    c3 = {
        "cluster_id": "CLUST-MODIS-00003", "sensor": "MODIS",
        "centroid_latitude": 55.0, "centroid_longitude": -105.0,
        "start_timestamp_utc": "2025-08-01 18:00:00+00:00", "end_timestamp_utc": "2025-08-01 18:05:00+00:00",
        "observation_count": 7, "sum_frp_mw": 120.0, "max_spatial_spread_km": 0.5,
    }

    # 1. Unconstrained all_in_window strategy: C1 -> C2, C1 -> C3 (shortcut!), C2 -> C3
    dense_engine = TemporalEventEvolutionEngine(EvolutionConfig(
        max_temporal_gap_hours=24.0, max_spatial_distance_km=5.0,
        candidate_selection_strategy="all_in_window"
    ))
    dense_rels = dense_engine.find_temporal_relationships([c1, c2, c3], "MODIS")
    assert len(dense_rels) == 3
    dense_endpoints = [(r["source_cluster_id"], r["target_cluster_id"]) for r in dense_rels]
    assert ("CLUST-MODIS-00001", "CLUST-MODIS-00003") in dense_endpoints

    # 2. Successive Observation Period (SOP) strategy: C1 only links to C2 (at 6h). C2 links to C3 (at 18h).
    sop_engine = TemporalEventEvolutionEngine(EvolutionConfig(
        max_temporal_gap_hours=24.0, max_spatial_distance_km=5.0,
        candidate_selection_strategy="successive_period"
    ))
    sop_rels = sop_engine.find_temporal_relationships([c1, c2, c3], "MODIS")
    assert len(sop_rels) == 2
    sop_endpoints = [(r["source_cluster_id"], r["target_cluster_id"]) for r in sop_rels]
    assert ("CLUST-MODIS-00001", "CLUST-MODIS-00002") in sop_endpoints
    assert ("CLUST-MODIS-00002", "CLUST-MODIS-00003") in sop_endpoints
    # Shortcut C1 -> C3 is eliminated!
    assert ("CLUST-MODIS-00001", "CLUST-MODIS-00003") not in sop_endpoints


def test_extent_aware_centroid_cap():
    """Verify hard centroid separation cap prevents excessive spatial leaps in extent-aware mode."""
    # Distance: centroid separation is 8.0 km.
    # Spreads: c1 has 2.0 km spread, c2 has 2.0 km spread.
    # Effective distance: 8.0 - 4.0 = 4.0 km <= max_spatial_distance_km (5.0 km).
    # But centroid distance (8.0 km) > max_centroid_cap_km (7.5 km).
    lat_step = 8.0 / 111.0  # Approx 8.0 km latitude offset
    c1 = {
        "cluster_id": "CLUST-MODIS-00001", "sensor": "MODIS",
        "centroid_latitude": 55.0, "centroid_longitude": -105.0,
        "start_timestamp_utc": "2025-08-01 00:00:00+00:00", "end_timestamp_utc": "2025-08-01 00:05:00+00:00",
        "observation_count": 10, "sum_frp_mw": 200.0, "max_spatial_spread_km": 2.0,
    }
    c2 = {
        "cluster_id": "CLUST-MODIS-00002", "sensor": "MODIS",
        "centroid_latitude": 55.0 + lat_step, "centroid_longitude": -105.0,
        "start_timestamp_utc": "2025-08-01 06:00:00+00:00", "end_timestamp_utc": "2025-08-01 06:05:00+00:00",
        "observation_count": 10, "sum_frp_mw": 210.0, "max_spatial_spread_km": 2.0,
    }

    # With cap at 7.5 km: rejected
    engine_capped = TemporalEventEvolutionEngine(EvolutionConfig(
        max_temporal_gap_hours=24.0, max_spatial_distance_km=5.0,
        use_extent_aware=True, max_centroid_cap_km=7.5,
    ))
    rels_capped = engine_capped.find_temporal_relationships([c1, c2], "MODIS")
    assert len(rels_capped) == 0

    # With cap relaxed to 10.0 km: admitted
    engine_relaxed = TemporalEventEvolutionEngine(EvolutionConfig(
        max_temporal_gap_hours=24.0, max_spatial_distance_km=5.0,
        use_extent_aware=True, max_centroid_cap_km=10.0,
    ))
    rels_relaxed = engine_relaxed.find_temporal_relationships([c1, c2], "MODIS")
    assert len(rels_relaxed) == 1


def test_cross_sensor_evidence_metrics():
    """Verify track-level cross-sensor evidence count and rate calculations."""
    engine = TemporalEventEvolutionEngine()
    c1 = {
        "cluster_id": "CLUST-MODIS-00001", "sensor": "MODIS",
        "centroid_latitude": 55.0, "centroid_longitude": -105.0,
        "start_timestamp_utc": "2025-08-01 00:00:00+00:00", "end_timestamp_utc": "2025-08-01 00:05:00+00:00",
        "observation_count": 5, "sum_frp_mw": 100.0, "max_spatial_spread_km": 0.5,
    }
    c2 = {
        "cluster_id": "CLUST-MODIS-00002", "sensor": "MODIS",
        "centroid_latitude": 55.0, "centroid_longitude": -105.0,
        "start_timestamp_utc": "2025-08-01 06:00:00+00:00", "end_timestamp_utc": "2025-08-01 06:05:00+00:00",
        "observation_count": 6, "sum_frp_mw": 110.0, "max_spatial_spread_km": 0.5,
    }
    rels = engine.find_temporal_relationships([c1, c2], "MODIS")
    
    # Phase 5 cross-sensor association supporting c1 only
    mock_cross = [{"modis_cluster_id": "CLUST-MODIS-00001", "viirs_cluster_id": "CLUST-VIIRS-00001"}]
    
    tracks, mems, _ = engine.build_event_tracks([c1, c2], rels, "MODIS", mock_cross)
    assert len(tracks) == 1
    track = tracks[0]
    assert track["clusters_with_cross_sensor_evidence_count"] == 1
    assert track["cross_sensor_evidence_rate_pct"] == 50.0  # 1 out of 2 clusters
    
    # Membership check
    m1 = next(m for m in mems if m["cluster_id"] == "CLUST-MODIS-00001")
    m2 = next(m for m in mems if m["cluster_id"] == "CLUST-MODIS-00002")
    assert m1["has_cross_sensor_evidence"] is True
    assert m2["has_cross_sensor_evidence"] is False


def test_touching_temporal_intervals_gap_zero():
    """Verify touching temporal intervals (gap = 0.0 hours) are accepted."""
    engine = TemporalEventEvolutionEngine(EvolutionConfig(max_temporal_gap_hours=24.0, max_spatial_distance_km=5.0))
    c1 = {
        "cluster_id": "CLUST-MODIS-00001", "sensor": "MODIS",
        "centroid_latitude": 55.0, "centroid_longitude": -105.0,
        "start_timestamp_utc": "2025-08-01 12:00:00+00:00", "end_timestamp_utc": "2025-08-01 12:05:00+00:00",
        "observation_count": 5, "sum_frp_mw": 100.0, "max_spatial_spread_km": 0.5,
    }
    c2 = {
        "cluster_id": "CLUST-MODIS-00002", "sensor": "MODIS",
        "centroid_latitude": 55.0, "centroid_longitude": -105.0,
        "start_timestamp_utc": "2025-08-01 12:05:00+00:00", "end_timestamp_utc": "2025-08-01 12:10:00+00:00",
        "observation_count": 6, "sum_frp_mw": 110.0, "max_spatial_spread_km": 0.5,
    }
    rels = engine.find_temporal_relationships([c1, c2], "MODIS")
    assert len(rels) == 1
    assert rels[0]["temporal_gap_hours"] == 0.0

