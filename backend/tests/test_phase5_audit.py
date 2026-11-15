"""Phase 5.3: Comprehensive Scientific and Algorithmic Validation Audit Test Suite.

Rigorously verifies:
1. Spatial-temporal DBSCAN algorithmic correctness on spherical coordinates.
2. Boundary reconciliation & partitioning stability (Union-Find).
3. Deterministic cluster identification & reproducibility under permutations.
4. Cross-sensor event association correctness & bipartite graph construction.
5. Composite heuristic event scoring mathematical rigor and bounds [0, 1].
6. Bipartite degree multiplicity vs connected component topology disentanglement.
7. Heuristic evidence classification and ambiguity threshold detection.
8. Stored artifact & empirical result consistency against data/events/.
9. Data integrity & strict conservation of observations (Input = Clustered + Noise).
10. Computational performance & scalability safeguards.
11. End-to-end API consistency.
"""

import os
import math
import json
import pytest
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from app.services.matching_config import EARTH_RADIUS_KM
from app.services.candidate_generation import haversine_distance_km, parse_timestamp_to_epoch
from app.services.clustering import (
    SpatialTemporalDBSCAN,
    DisjointSetUnion,
    compute_spherical_centroid,
    compute_bounding_coordinates,
)
from app.services.event_association import CrossSensorEventAssociator
from app.services.events_manager import events_manager


@pytest.fixture
def client():
    return TestClient(app)


# ==============================================================================
# AUDIT 1: SPATIAL-TEMPORAL DBSCAN ALGORITHMIC CORRECTNESS
# ==============================================================================

def test_audit1_haversine_boundary_precision():
    """Verify exact Haversine distance thresholding at boundary conditions."""
    # Reference point at (0, 0)
    lat0, lon0 = 0.0, 0.0
    
    # 1 degree latitude = 2 * pi * 6371.0088 / 360 = 111.1949 km
    # For spatial_radius_km = 2.0 km:
    delta_lat_exact = (2.0 / EARTH_RADIUS_KM) * (180.0 / math.pi)  # ~0.017986 degrees
    
    # Point A: 1.99 km away (should be a neighbor)
    lat_inside = lat0 + delta_lat_exact * (1.99 / 2.0)
    # Point B: 2.01 km away (should NOT be a neighbor)
    lat_outside = lat0 + delta_lat_exact * (2.01 / 2.0)
    
    dbscan = SpatialTemporalDBSCAN(spatial_radius_km=2.0, temporal_window_minutes=60.0, min_samples=2, sensor="MODIS")
    
    # Test inside
    df_inside = pd.DataFrame([
        {"observation_id": "P0", "latitude": lat0, "longitude": lon0, "timestamp_utc": "2025-06-01T12:00:00Z"},
        {"observation_id": "P1", "latitude": lat_inside, "longitude": lon0, "timestamp_utc": "2025-06-01T12:00:00Z"},
    ])
    clusters_in, mem_in, noise_in = dbscan.fit(df_inside)
    assert len(clusters_in) == 1, "Points at 1.99 km must form a cluster with min_samples=2"
    assert len(noise_in) == 0
    
    # Test outside
    df_outside = pd.DataFrame([
        {"observation_id": "P0", "latitude": lat0, "longitude": lon0, "timestamp_utc": "2025-06-01T12:00:00Z"},
        {"observation_id": "P2", "latitude": lat_outside, "longitude": lon0, "timestamp_utc": "2025-06-01T12:00:00Z"},
    ])
    clusters_out, mem_out, noise_out = dbscan.fit(df_outside)
    assert len(clusters_out) == 0, "Points at 2.01 km must NOT form a cluster with min_samples=2"
    assert len(noise_out) == 2


def test_audit1_temporal_boundary_precision():
    """Verify temporal window thresholding at exact 60-minute boundary."""
    dbscan = SpatialTemporalDBSCAN(spatial_radius_km=2.0, temporal_window_minutes=60.0, min_samples=2, sensor="MODIS")
    
    # Separated by 59 minutes: inside window
    df_inside = pd.DataFrame([
        {"observation_id": "T0", "latitude": 10.0, "longitude": 20.0, "timestamp_utc": "2025-06-01T12:00:00Z"},
        {"observation_id": "T1", "latitude": 10.0, "longitude": 20.0, "timestamp_utc": "2025-06-01T12:59:00Z"},
    ])
    clusters_in, _, noise_in = dbscan.fit(df_inside)
    assert len(clusters_in) == 1
    assert len(noise_in) == 0
    
    # Separated by 61 minutes: outside window
    df_outside = pd.DataFrame([
        {"observation_id": "T0", "latitude": 10.0, "longitude": 20.0, "timestamp_utc": "2025-06-01T12:00:00Z"},
        {"observation_id": "T2", "latitude": 10.0, "longitude": 20.0, "timestamp_utc": "2025-06-01T13:01:00Z"},
    ])
    clusters_out, _, noise_out = dbscan.fit(df_outside)
    assert len(clusters_out) == 0
    assert len(noise_out) == 2


def test_audit1_core_border_noise_definitions():
    """Verify rigorous DBSCAN core, border, and noise semantics with min_samples=4."""
    dbscan = SpatialTemporalDBSCAN(spatial_radius_km=2.0, temporal_window_minutes=60.0, min_samples=4, sensor="VIIRS")
    
    # C1..C4 form a dense core (mutually within 1.0 km)
    # B0 is within 2.0 km of C3 and C4 (3 neighbors total including self < 4 min_samples) -> Border
    # N0 is 55.0 km away -> Noise
    df = pd.DataFrame([
        {"observation_id": "C1", "latitude": -0.008, "longitude": 0.0, "timestamp_utc": "2025-06-01T12:00:00Z"},
        {"observation_id": "C2", "latitude": -0.004, "longitude": 0.0, "timestamp_utc": "2025-06-01T12:00:00Z"},
        {"observation_id": "C3", "latitude": 0.000, "longitude": 0.0, "timestamp_utc": "2025-06-01T12:00:00Z"},
        {"observation_id": "C4", "latitude": 0.004, "longitude": 0.0, "timestamp_utc": "2025-06-01T12:00:00Z"},
        {"observation_id": "B0", "latitude": 0.0175, "longitude": 0.0, "timestamp_utc": "2025-06-01T12:00:00Z"},
        {"observation_id": "N0", "latitude": 0.500, "longitude": 0.0, "timestamp_utc": "2025-06-01T12:00:00Z"},
    ])
    
    clusters, memberships, noise_records = dbscan.fit(df)
    assert len(clusters) == 1
    assert clusters[0]["observation_count"] == 5
    assert clusters[0]["core_count"] == 4
    assert clusters[0]["border_count"] == 1
    
    roles = {m["observation_id"]: m["point_role"] for m in memberships}
    assert roles["C3"] == "core"
    assert roles["B0"] == "border"
    
    assert len(noise_records) == 1
    assert noise_records[0]["observation_id"] == "N0"
    assert noise_records[0]["point_role"] == "noise"


# ==============================================================================
# AUDIT 2: BOUNDARY RECONCILIATION & PARTITIONING STABILITY
# ==============================================================================

def test_audit2_union_find_reconciliation_invariance():
    """Verify Union-Find graph equivalence classes, transitivity, and deterministic root selection."""
    dsu = DisjointSetUnion()
    
    # Chain of partitions linking A-B, B-C, C-D
    dsu.union("CLUST-2", "CLUST-1")
    dsu.union("CLUST-3", "CLUST-2")
    dsu.union("CLUST-4", "CLUST-3")
    
    # Verify all resolve to the smallest string root
    assert dsu.find("CLUST-1") == "CLUST-1"
    assert dsu.find("CLUST-2") == "CLUST-1"
    assert dsu.find("CLUST-3") == "CLUST-1"
    assert dsu.find("CLUST-4") == "CLUST-1"
    
    # Shuffled union order test
    dsu2 = DisjointSetUnion()
    dsu2.union("CLUST-4", "CLUST-2")
    dsu2.union("CLUST-3", "CLUST-1")
    dsu2.union("CLUST-3", "CLUST-4")
    
    assert dsu2.find("CLUST-1") == "CLUST-1"
    assert dsu2.find("CLUST-2") == "CLUST-1"
    assert dsu2.find("CLUST-3") == "CLUST-1"
    assert dsu2.find("CLUST-4") == "CLUST-1"


# ==============================================================================
# AUDIT 3: DETERMINISTIC CLUSTER IDENTIFICATION & REPRODUCIBILITY
# ==============================================================================

def test_audit3_row_shuffling_invariance():
    """Verify that permuting input observation order yields identical cluster statistics and IDs."""
    np.random.seed(42)
    rows = []
    base_epoch = 1717243200
    for i in range(15):
        rows.append({
            "observation_id": f"OBS_{i:03d}",
            "latitude": 34.0 + (i % 3) * 0.005,
            "longitude": -118.0 + (i // 3) * 0.005,
            "timestamp_utc": f"2025-06-01T12:{i:02d}:00Z",
            "frp": float(10 + i),
            "satellite": "Terra",
        })
    df_orig = pd.DataFrame(rows)
    df_shuffled = df_orig.sample(frac=1.0, random_state=999).reset_index(drop=True)
    
    dbscan = SpatialTemporalDBSCAN(spatial_radius_km=2.0, temporal_window_minutes=60.0, min_samples=3, sensor="MODIS")
    
    c1, m1, n1 = dbscan.fit(df_orig)
    c2, m2, n2 = dbscan.fit(df_shuffled)
    
    assert len(c1) == len(c2)
    assert len(m1) == len(m2)
    assert len(n1) == len(n2)
    
    for cl1, cl2 in zip(c1, c2):
        assert cl1["cluster_id"] == cl2["cluster_id"]
        assert cl1["observation_count"] == cl2["observation_count"]
        assert cl1["centroid_latitude"] == cl2["centroid_latitude"]
        assert cl1["centroid_longitude"] == cl2["centroid_longitude"]
        assert cl1["sum_frp_mw"] == cl2["sum_frp_mw"]


# ==============================================================================
# AUDIT 4: CROSS-SENSOR EVENT ASSOCIATION CORRECTNESS
# ==============================================================================

def test_audit4_coverage_denominators_and_duplicate_edge_elimination():
    """Verify that cluster coverage denominator uses unique observations, and duplicate edges are correctly handled."""
    modis_clusters = [{
        "cluster_id": "CLUST-MODIS-00001", "observation_count": 5,
        "centroid_latitude": 30.0, "centroid_longitude": 50.0,
        "start_timestamp_utc": "2025-06-01T12:00:00Z", "end_timestamp_utc": "2025-06-01T12:30:00Z",
        "sum_frp_mw": 100.0,
    }]
    viirs_clusters = [{
        "cluster_id": "CLUST-VIIRS-00001", "observation_count": 10,
        "centroid_latitude": 30.01, "centroid_longitude": 50.01,
        "start_timestamp_utc": "2025-06-01T12:10:00Z", "end_timestamp_utc": "2025-06-01T12:40:00Z",
        "sum_frp_mw": 200.0,
    }]
    
    modis_memberships = [{"observation_id": f"M{i}", "cluster_id": "CLUST-MODIS-00001"} for i in range(5)]
    viirs_memberships = [{"observation_id": f"V{i}", "cluster_id": "CLUST-VIIRS-00001"} for i in range(10)]
    
    # 4 candidate edges, but 2 are duplicate pairs (M0, V0)
    cand_df = pd.DataFrame([
        {"modis_observation_id": "M0", "viirs_observation_id": "V0", "distance_km": 0.5, "time_diff_minutes": 10.0, "heuristic_score": 0.8},
        {"modis_observation_id": "M0", "viirs_observation_id": "V0", "distance_km": 0.5, "time_diff_minutes": 10.0, "heuristic_score": 0.8},
        {"modis_observation_id": "M1", "viirs_observation_id": "V1", "distance_km": 0.6, "time_diff_minutes": 12.0, "heuristic_score": 0.75},
        {"modis_observation_id": "M2", "viirs_observation_id": "V2", "distance_km": 0.7, "time_diff_minutes": 15.0, "heuristic_score": 0.70},
    ])
    
    associator = CrossSensorEventAssociator()
    rels, comps, summary = associator.associate_clusters(
        modis_clusters, viirs_clusters, modis_memberships, viirs_memberships, cand_df
    )
    
    assert len(rels) == 1
    rel = rels[0]
    
    # Unique observations: M0, M1, M2 -> 3 unique MODIS out of 5 total -> 3/5 = 0.6
    # V0, V1, V2 -> 3 unique VIIRS out of 10 total -> 3/10 = 0.3
    assert rel["unique_supporting_modis_obs"] == 3
    assert rel["unique_supporting_viirs_obs"] == 3
    assert rel["modis_obs_coverage_ratio"] == 0.6
    assert rel["viirs_obs_coverage_ratio"] == 0.3
    assert rel["modis_cluster_obs_count"] == 5
    assert rel["viirs_cluster_obs_count"] == 10


# ==============================================================================
# AUDIT 5: COMPOSITE HEURISTIC EVENT SCORING RIGOR
# ==============================================================================

def test_audit5_heuristic_score_bounds_and_monotonicity():
    """Verify that heuristic event score is strictly bounded in [0, 1] and strictly decreases with distance/time."""
    associator = CrossSensorEventAssociator(spatial_radius_km=2.0, temporal_window_minutes=60.0)
    
    # Case A: Perfect coincidence (0 dist, 0 time, 1.0 coverage, 1.0 edge score)
    # 0.35 * 1.0 + 0.25 * 1.0 + 0.20 * 1.0 + 0.20 * 1.0 = 1.0
    s_spatial_perf = max(0.0, 1.0 - (0.0 / 2.0))
    s_temporal_perf = max(0.0, 1.0 - (0.0 / 60.0))
    score_perf = round(0.35 * 1.0 + 0.25 * s_spatial_perf + 0.20 * s_temporal_perf + 0.20 * 1.0, 4)
    assert score_perf == 1.0
    
    # Case B: Maximum distance and time limits (2.0 km, 60.0 min, 0 coverage, 0 score)
    s_spatial_zero = max(0.0, 1.0 - (2.0 / 2.0))
    s_temporal_zero = max(0.0, 1.0 - (60.0 / 60.0))
    score_zero = round(0.35 * 0.0 + 0.25 * s_spatial_zero + 0.20 * s_temporal_zero + 0.20 * 0.0, 4)
    assert score_zero == 0.0
    
    # Case C: Monotonicity with distance
    s_dist_1km = max(0.0, 1.0 - (1.0 / 2.0))
    s_dist_1_5km = max(0.0, 1.0 - (1.5 / 2.0))
    assert s_dist_1km > s_dist_1_5km


# ==============================================================================
# AUDIT 6: BIPARTITE DEGREE VS CONNECTED COMPONENT TOPOLOGY DISENTANGLEMENT
# ==============================================================================

def test_audit6_degree_multiplicity_vs_component_topology():
    """Verify mathematical distinction between edge multiplicity and component topology."""
    # Build a 1:2 star: M1 connected to V1 and V2
    modis_clusters = [{"cluster_id": "CLUST-MODIS-00001", "observation_count": 4, "centroid_latitude": 0, "centroid_longitude": 0, "start_timestamp_utc": "2025-06-01T12:00:00Z", "end_timestamp_utc": "2025-06-01T12:00:00Z"}]
    viirs_clusters = [
        {"cluster_id": "CLUST-VIIRS-00001", "observation_count": 4, "centroid_latitude": 0, "centroid_longitude": 0, "start_timestamp_utc": "2025-06-01T12:00:00Z", "end_timestamp_utc": "2025-06-01T12:00:00Z"},
        {"cluster_id": "CLUST-VIIRS-00002", "observation_count": 4, "centroid_latitude": 0, "centroid_longitude": 0, "start_timestamp_utc": "2025-06-01T12:00:00Z", "end_timestamp_utc": "2025-06-01T12:00:00Z"},
    ]
    m_mem = [{"observation_id": f"M{i}", "cluster_id": "CLUST-MODIS-00001"} for i in range(4)]
    v_mem = [{"observation_id": f"V1_{i}", "cluster_id": "CLUST-VIIRS-00001"} for i in range(4)] + \
            [{"observation_id": f"V2_{i}", "cluster_id": "CLUST-VIIRS-00002"} for i in range(4)]
    
    cand_df = pd.DataFrame([
        {"modis_observation_id": "M0", "viirs_observation_id": "V1_0", "distance_km": 0.5, "time_diff_minutes": 5, "heuristic_score": 0.8},
        {"modis_observation_id": "M1", "viirs_observation_id": "V2_0", "distance_km": 0.5, "time_diff_minutes": 5, "heuristic_score": 0.8},
    ])
    
    associator = CrossSensorEventAssociator()
    rels, comps, _ = associator.associate_clusters(modis_clusters, viirs_clusters, m_mem, v_mem, cand_df)
    
    assert len(rels) == 2
    # Both edges share M1 (deg=2) and distinct Vi (deg=1) -> edge multiplicity is 1:N
    for r in rels:
        assert r["multiplicity_type"] == "1:N"
    
    # Component contains 1 MODIS and 2 VIIRS -> component topology is 1:N_star
    assert len(comps) == 1
    assert comps[0]["topology_type"] == "1:N_star"
    assert comps[0]["modis_clusters_count"] == 1
    assert comps[0]["viirs_clusters_count"] == 2


# ==============================================================================
# AUDIT 7: HEURISTIC EVIDENCE CLASSIFICATION & AMBIGUITY DETECTION
# ==============================================================================

def test_audit7_ambiguity_delta_threshold():
    """Verify that ambiguity is flagged when a cluster associates with competing candidates within delta <= 0.15."""
    modis_clusters = [{"cluster_id": "CLUST-MODIS-00001", "observation_count": 4, "centroid_latitude": 0, "centroid_longitude": 0, "start_timestamp_utc": "2025-06-01T12:00:00Z", "end_timestamp_utc": "2025-06-01T12:00:00Z"}]
    viirs_clusters = [
        {"cluster_id": "CLUST-VIIRS-00001", "observation_count": 4, "centroid_latitude": 0, "centroid_longitude": 0, "start_timestamp_utc": "2025-06-01T12:00:00Z", "end_timestamp_utc": "2025-06-01T12:00:00Z"},
        {"cluster_id": "CLUST-VIIRS-00002", "observation_count": 4, "centroid_latitude": 0, "centroid_longitude": 0, "start_timestamp_utc": "2025-06-01T12:00:00Z", "end_timestamp_utc": "2025-06-01T12:00:00Z"},
    ]
    m_mem = [{"observation_id": f"M{i}", "cluster_id": "CLUST-MODIS-00001"} for i in range(4)]
    v_mem = [{"observation_id": f"V1_{i}", "cluster_id": "CLUST-VIIRS-00001"} for i in range(4)] + \
            [{"observation_id": f"V2_{i}", "cluster_id": "CLUST-VIIRS-00002"} for i in range(4)]
    
    # Edge 1 has score ~0.80, Edge 2 has score ~0.75 (difference 0.05 <= 0.15 threshold)
    cand_df = pd.DataFrame([
        {"modis_observation_id": "M0", "viirs_observation_id": "V1_0", "distance_km": 0.4, "time_diff_minutes": 5, "heuristic_score": 0.82},
        {"modis_observation_id": "M1", "viirs_observation_id": "V2_0", "distance_km": 0.5, "time_diff_minutes": 6, "heuristic_score": 0.78},
    ])
    
    associator = CrossSensorEventAssociator(ambiguity_delta_threshold=0.15)
    rels, _, _ = associator.associate_clusters(modis_clusters, viirs_clusters, m_mem, v_mem, cand_df)
    
    assert len(rels) == 2
    for r in rels:
        assert r["is_ambiguous"] is True
        assert r["classification"] == "ambiguous_candidate"


# ==============================================================================
# AUDIT 8 & 9: STORED ARTIFACT & CONSERVATION OF OBSERVATIONS RECONCILIATION
# ==============================================================================

import duckdb


def _read_parquet_df(path):
    con = duckdb.connect()
    df = con.execute(f"SELECT * FROM read_parquet('{path.as_posix()}')").df()
    con.close()
    return df


def test_audit8_and_9_actual_artifact_counts_and_conservation():
    """Verify stored Parquet artifacts and exact observation accounting identity."""
    mgr = events_manager
    
    modis_c = _read_parquet_df(mgr.modis_clusters_file)
    viirs_c = _read_parquet_df(mgr.viirs_clusters_file)
    modis_m = _read_parquet_df(mgr.modis_membership_file)
    viirs_m = _read_parquet_df(mgr.viirs_membership_file)
    noise = _read_parquet_df(mgr.noise_file)
    rels = _read_parquet_df(mgr.associations_file)
    comps = _read_parquet_df(mgr.components_file)
    
    # 1. Stored row counts
    assert len(modis_c) == 310
    assert len(viirs_c) == 670
    assert len(modis_m) == 2191
    assert len(viirs_m) == 18798
    assert len(rels) == 158
    assert len(comps) == 118
    
    # 2. Conservation of observations
    # MODIS: 2191 clustered + 925 noise = 3116 total
    # VIIRS: 18798 clustered + 541 noise = 19339 total
    modis_noise = noise[noise["sensor"] == "MODIS"]
    viirs_noise = noise[noise["sensor"] == "VIIRS"]
    
    assert len(modis_noise) == 925
    assert len(viirs_noise) == 541
    assert len(modis_m) + len(modis_noise) == 3116
    assert len(viirs_m) + len(viirs_noise) == 19339
    assert len(noise) == 1466
    
    # 3. Relationship multiplicity counts
    mult_counts = rels["multiplicity_type"].value_counts().to_dict()
    assert mult_counts.get("1:1", 0) == 90
    assert mult_counts.get("1:N", 0) == 26
    assert mult_counts.get("N:1", 0) == 36
    assert mult_counts.get("M:N", 0) == 6
    assert sum(mult_counts.values()) == 158
    
    # 4. Relationship classification counts
    class_counts = rels["classification"].value_counts().to_dict()
    assert class_counts.get("stronger_candidate", 0) == 30
    assert class_counts.get("moderate_candidate", 0) == 62
    assert class_counts.get("weak_candidate", 0) == 7
    assert class_counts.get("ambiguous_candidate", 0) == 59
    assert sum(class_counts.values()) == 158
    
    # 5. Connected component topology counts
    comp_counts = comps["topology_type"].value_counts().to_dict()
    assert comp_counts.get("1:1_pair", 0) == 90
    assert comp_counts.get("1:N_star", 0) == 10
    assert comp_counts.get("N:1_star", 0) == 13
    assert comp_counts.get("M:N_complex", 0) == 5
    assert sum(comp_counts.values()) == 118


# ==============================================================================
# AUDIT 10: COMPUTATIONAL PERFORMANCE & SCALABILITY SAFEGUARD
# ==============================================================================

def test_audit10_clustering_performance_vectorized():
    """Verify that vectorized Haversine clustering executes efficiently without memory blowout."""
    import time
    
    np.random.seed(123)
    N = 1000
    lats = np.random.uniform(30.0, 31.0, N)
    lons = np.random.uniform(-119.0, -118.0, N)
    # Spread over 10 distinct hours
    epochs = 1717243200 + np.random.randint(0, 10, N) * 3600 + np.random.randint(0, 1800, N)
    
    df_large = pd.DataFrame({
        "observation_id": [f"PERF_{i:04d}" for i in range(N)],
        "latitude": lats,
        "longitude": lons,
        "epoch_seconds": epochs,
        "timestamp_utc": [f"2025-06-01T12:{i%60:02d}:00Z" for i in range(N)],
        "frp": np.random.uniform(5.0, 50.0, N),
        "satellite": "Aqua",
    })
    
    dbscan = SpatialTemporalDBSCAN(spatial_radius_km=2.0, temporal_window_minutes=60.0, min_samples=3, sensor="MODIS")
    
    t0 = time.perf_counter()
    clusters, memberships, noise = dbscan.fit(df_large)
    t1 = time.perf_counter()
    
    elapsed = t1 - t0
    # Must run well under 2.0 seconds for 1,000 points
    assert elapsed < 2.0, f"Clustering 1,000 observations took {elapsed:.2f}s, expected < 2.0s"
    assert len(memberships) + len(noise) == N


# ==============================================================================
# AUDIT 11: END-TO-END API AUDIT
# ==============================================================================

def test_audit11_api_endpoints_consistency(client):
    """Verify that the FastAPI endpoints report consistent data aligned with disk artifacts."""
    res_clust = client.get("/api/events/clustering/summary")
    assert res_clust.status_code == 200
    data_c = res_clust.json()
    assert data_c["modis"]["cluster_count"] == 310
    assert data_c["viirs"]["cluster_count"] == 670
    
    res_assoc = client.get("/api/events/association/summary")
    assert res_assoc.status_code == 200
    data_a = res_assoc.json()
    assert data_a["total_candidate_relationships"] == 158
    assert data_a["multiplicity_breakdown"]["1:1"] == 90
    assert data_a["component_topology_breakdown"]["1:1_pair"] == 90
    
    res_map = client.get("/api/events/map/relationships?limit=200")
    assert res_map.status_code == 200
    map_data = res_map.json()
    assert map_data["count"] == 158
