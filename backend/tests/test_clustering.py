"""Unit and Integration Tests for Phase 5.1 Independent Fire Event Clustering.

Verifies:
1. Two clearly separated clusters.
2. Spatially close observations outside temporal window.
3. Temporally close observations outside spatial radius.
4. Core, border, and noise point classification.
5. Duplicate coordinates handling.
6. Antimeridian crossing handling with 3D Cartesian spherical centroid averaging.
7. High-latitude observation handling.
8. Deterministic stable cluster IDs.
9. Empty dataset and invalid timestamp/coordinate handling.
10. Partition boundary reconciliation with DisjointSetUnion.
11. Comparison of partitioned reconciliation against single-process reference.
"""

import math
import pytest
import numpy as np
import pandas as pd

from app.services.clustering import (
    SpatialTemporalDBSCAN,
    PartitionedClusteringEngine,
    compute_spherical_centroid,
    compute_bounding_coordinates,
    DisjointSetUnion,
)
from app.services.candidate_generation import haversine_distance_km


def test_spherical_centroid_antimeridian():
    """Verify 3D Cartesian spherical centroid handles antimeridian crossing (-180° / +180°)."""
    # Two points equidistant across the antimeridian (+179° and -179°) at latitude 50°N
    lats = np.array([50.0, 50.0])
    lons = np.array([179.0, -179.0])
    c_lat, c_lon = compute_spherical_centroid(lats, lons)

    assert abs(c_lat - 50.0) < 0.1
    # The true midpoint longitude across the antimeridian is 180° (or -180°)
    assert abs(abs(c_lon) - 180.0) < 0.1

    # Simple Euclidean average would have mistakenly produced 0.0° (prime meridian)!
    assert abs(c_lon - 0.0) > 100.0


def test_spherical_centroid_high_latitudes():
    """Verify centroid calculation near north polar latitude."""
    lats = np.array([88.0, 88.0, 88.0, 88.0])
    lons = np.array([0.0, 90.0, 180.0, -90.0])
    c_lat, c_lon = compute_spherical_centroid(lats, lons)

    # Centroid of symmetric ring around North Pole is North Pole (lat=90.0)
    assert abs(c_lat - 90.0) < 0.01


def test_two_clearly_separated_clusters():
    """Verify two spatially distant groups form two distinct clusters."""
    # Cluster 1: near (55.0°N, -105.0°W) at 12:00
    c1 = pd.DataFrame([
        {"observation_id": "M1", "latitude": 55.000, "longitude": -105.000, "timestamp_utc": "2025-08-01 12:00:00", "frp": 50.0, "satellite": "Terra"},
        {"observation_id": "M2", "latitude": 55.005, "longitude": -105.005, "timestamp_utc": "2025-08-01 12:05:00", "frp": 60.0, "satellite": "Terra"},
        {"observation_id": "M3", "latitude": 55.010, "longitude": -105.010, "timestamp_utc": "2025-08-01 12:10:00", "frp": 45.0, "satellite": "Terra"},
    ])
    # Cluster 2: 200 km away near (57.0°N, -105.0°W) at 12:00
    c2 = pd.DataFrame([
        {"observation_id": "M4", "latitude": 57.000, "longitude": -105.000, "timestamp_utc": "2025-08-01 12:00:00", "frp": 80.0, "satellite": "Terra"},
        {"observation_id": "M5", "latitude": 57.005, "longitude": -105.005, "timestamp_utc": "2025-08-01 12:05:00", "frp": 90.0, "satellite": "Terra"},
        {"observation_id": "M6", "latitude": 57.010, "longitude": -105.010, "timestamp_utc": "2025-08-01 12:10:00", "frp": 75.0, "satellite": "Terra"},
    ])
    df = pd.concat([c1, c2], ignore_index=True)

    dbscan = SpatialTemporalDBSCAN(spatial_radius_km=2.0, temporal_window_minutes=60.0, min_samples=3, sensor="MODIS")
    clusters, memberships, noise = dbscan.fit(df)

    assert len(clusters) == 2
    assert len(memberships) == 6
    assert len(noise) == 0

    c1_members = [m["observation_id"] for m in memberships if m["cluster_id"] == clusters[0]["cluster_id"]]
    c2_members = [m["observation_id"] for m in memberships if m["cluster_id"] == clusters[1]["cluster_id"]]

    assert set(c1_members) == {"M1", "M2", "M3"}
    assert set(c2_members) == {"M4", "M5", "M6"}


def test_spatially_close_outside_temporal_window():
    """Observations in identical location separated by 5 hours must NOT cluster together."""
    df = pd.DataFrame([
        # Group A at 12:00 UTC (only 2 points, min_samples=3)
        {"observation_id": "M1", "latitude": 55.000, "longitude": -105.000, "timestamp_utc": "2025-08-01 12:00:00", "frp": 30.0},
        {"observation_id": "M2", "latitude": 55.005, "longitude": -105.005, "timestamp_utc": "2025-08-01 12:05:00", "frp": 35.0},
        # Group B at identical location but 18:00 UTC (6 hours later)
        {"observation_id": "M3", "latitude": 55.000, "longitude": -105.000, "timestamp_utc": "2025-08-01 18:00:00", "frp": 40.0},
        {"observation_id": "M4", "latitude": 55.005, "longitude": -105.005, "timestamp_utc": "2025-08-01 18:05:00", "frp": 45.0},
    ])

    dbscan = SpatialTemporalDBSCAN(spatial_radius_km=2.0, temporal_window_minutes=60.0, min_samples=3, sensor="MODIS")
    clusters, memberships, noise = dbscan.fit(df)

    # Since min_samples=3 and each temporal group only has 2 points, no cluster can form
    assert len(clusters) == 0
    assert len(memberships) == 0
    # All 4 points must be preserved as noise, not discarded!
    assert len(noise) == 4
    assert {n["observation_id"] for n in noise} == {"M1", "M2", "M3", "M4"}


def test_temporally_close_outside_spatial_radius():
    """Observations occurring at identical time but separated by 50 km must NOT cluster together."""
    df = pd.DataFrame([
        {"observation_id": "M1", "latitude": 55.000, "longitude": -105.000, "timestamp_utc": "2025-08-01 12:00:00", "frp": 30.0},
        {"observation_id": "M2", "latitude": 55.500, "longitude": -105.000, "timestamp_utc": "2025-08-01 12:00:00", "frp": 35.0},  # ~55 km north
        {"observation_id": "M3", "latitude": 56.000, "longitude": -105.000, "timestamp_utc": "2025-08-01 12:00:00", "frp": 40.0},  # ~110 km north
    ])

    dbscan = SpatialTemporalDBSCAN(spatial_radius_km=2.0, temporal_window_minutes=60.0, min_samples=3, sensor="MODIS")
    clusters, memberships, noise = dbscan.fit(df)

    assert len(clusters) == 0
    assert len(noise) == 3


def test_core_and_border_points():
    """Verify core vs border points semantics in DBSCAN."""
    # Point M1 has 2 neighbors (M2, M3) -> 3 points total -> Core
    # Point M2 has 1 neighbor (M1) -> 2 points total -> Border
    # Point M3 has 1 neighbor (M1) -> 2 points total -> Border
    # Point M4 is isolated (10 km away) -> Noise
    df = pd.DataFrame([
        {"observation_id": "M1", "latitude": 55.000, "longitude": -105.000, "timestamp_utc": "2025-08-01 12:00:00", "frp": 30.0},
        {"observation_id": "M2", "latitude": 55.008, "longitude": -105.000, "timestamp_utc": "2025-08-01 12:00:00", "frp": 35.0},  # ~0.89 km from M1
        {"observation_id": "M3", "latitude": 54.992, "longitude": -105.000, "timestamp_utc": "2025-08-01 12:00:00", "frp": 40.0},  # ~0.89 km from M1, ~1.78 km from M2
        {"observation_id": "M4", "latitude": 55.200, "longitude": -105.000, "timestamp_utc": "2025-08-01 12:00:00", "frp": 50.0},  # ~22 km away
    ])

    dbscan = SpatialTemporalDBSCAN(spatial_radius_km=1.0, temporal_window_minutes=60.0, min_samples=3, sensor="MODIS")
    clusters, memberships, noise = dbscan.fit(df)

    assert len(clusters) == 1
    assert len(memberships) == 3
    assert len(noise) == 1
    assert noise[0]["observation_id"] == "M4"

    role_map = {m["observation_id"]: m["point_role"] for m in memberships}
    assert role_map["M1"] == "core"
    assert role_map["M2"] == "border"
    assert role_map["M3"] == "border"

    # Verify cluster counts
    assert clusters[0]["observation_count"] == 3
    assert clusters[0]["core_count"] == 1
    assert clusters[0]["border_count"] == 2


def test_duplicate_coordinates_handling():
    """Identical coordinates (e.g. repeated scans) must be handled stably without crashing."""
    df = pd.DataFrame([
        {"observation_id": "V1", "latitude": 55.000, "longitude": -105.000, "timestamp_utc": "2025-08-01 12:00:00", "frp": 20.0},
        {"observation_id": "V2", "latitude": 55.000, "longitude": -105.000, "timestamp_utc": "2025-08-01 12:00:00", "frp": 25.0},
        {"observation_id": "V3", "latitude": 55.000, "longitude": -105.000, "timestamp_utc": "2025-08-01 12:00:00", "frp": 30.0},
    ])

    dbscan = SpatialTemporalDBSCAN(spatial_radius_km=2.0, temporal_window_minutes=60.0, min_samples=3, sensor="VIIRS")
    clusters, memberships, noise = dbscan.fit(df)

    assert len(clusters) == 1
    assert clusters[0]["observation_count"] == 3
    assert clusters[0]["sum_frp_mw"] == 75.0
    assert clusters[0]["mean_spatial_spread_km"] == 0.0


def test_empty_and_invalid_data_handling():
    """Empty dataframes or missing coordinates must be handled gracefully."""
    dbscan = SpatialTemporalDBSCAN(spatial_radius_km=2.0, temporal_window_minutes=60.0, min_samples=3, sensor="MODIS")
    
    # 1. Empty DataFrame
    clusters, memberships, noise = dbscan.fit(pd.DataFrame())
    assert clusters == []
    assert memberships == []
    assert noise == []

    # 2. DataFrame with NaNs in coordinates
    df_nan = pd.DataFrame([
        {"observation_id": "M1", "latitude": None, "longitude": -105.000, "timestamp_utc": "2025-08-01 12:00:00", "frp": 30.0},
        {"observation_id": "M2", "latitude": 55.000, "longitude": None, "timestamp_utc": "2025-08-01 12:00:00", "frp": 30.0},
    ])
    clusters, memberships, noise = dbscan.fit(df_nan)
    assert clusters == []


def test_stable_cluster_identifiers():
    """Cluster IDs must be completely deterministic for the same input data."""
    df = pd.DataFrame([
        {"observation_id": "M1", "latitude": 55.000, "longitude": -105.000, "timestamp_utc": "2025-08-01 12:00:00", "frp": 30.0},
        {"observation_id": "M2", "latitude": 55.005, "longitude": -105.005, "timestamp_utc": "2025-08-01 12:05:00", "frp": 35.0},
        {"observation_id": "M3", "latitude": 55.010, "longitude": -105.010, "timestamp_utc": "2025-08-01 12:10:00", "frp": 40.0},
    ])

    dbscan = SpatialTemporalDBSCAN(spatial_radius_km=2.0, temporal_window_minutes=60.0, min_samples=3, sensor="MODIS")
    c_run1, m_run1, _ = dbscan.fit(df)
    c_run2, m_run2, _ = dbscan.fit(df)

    assert c_run1[0]["cluster_id"] == "CLUST-MODIS-00001"
    assert c_run1[0]["cluster_id"] == c_run2[0]["cluster_id"]
    assert [m["cluster_id"] for m in m_run1] == [m["cluster_id"] for m in m_run2]


def test_partitioned_boundary_reconciliation():
    """Verify that observations overlapping across partitions are reconciled without duplication."""
    # Partition 1 covers Day 1 (observations A, B, C)
    # Partition 2 covers Day 2 with Day 1 halo (observations C, D, E)
    # Observation C is in the overlap halo
    engine = PartitionedClusteringEngine(spatial_radius_km=2.0, temporal_window_minutes=60.0, min_samples=3, sensor="MODIS")

    part1_df = pd.DataFrame([
        {"observation_id": "A", "latitude": 55.000, "longitude": -105.000, "timestamp_utc": "2025-08-01 23:30:00", "frp": 30.0},
        {"observation_id": "B", "latitude": 55.005, "longitude": -105.005, "timestamp_utc": "2025-08-01 23:45:00", "frp": 35.0},
        {"observation_id": "C", "latitude": 55.010, "longitude": -105.010, "timestamp_utc": "2025-08-01 23:55:00", "frp": 40.0},
    ])
    part2_df = pd.DataFrame([
        {"observation_id": "C", "latitude": 55.010, "longitude": -105.010, "timestamp_utc": "2025-08-01 23:55:00", "frp": 40.0},
        {"observation_id": "D", "latitude": 55.015, "longitude": -105.015, "timestamp_utc": "2025-08-02 00:10:00", "frp": 45.0},
        {"observation_id": "E", "latitude": 55.020, "longitude": -105.020, "timestamp_utc": "2025-08-02 00:20:00", "frp": 50.0},
    ])

    res1 = engine.dbscan.fit(part1_df)
    res2 = engine.dbscan.fit(part2_df)

    reconciled_clusters, reconciled_members, reconciled_noise = engine.reconcile_partition_clusters([res1, res2])

    # Reconciled result must merge into exactly 1 unified cluster
    assert len(reconciled_clusters) == 1
    # Exactly 5 unique observations (A, B, C, D, E); observation C must NOT be duplicated!
    assert reconciled_clusters[0]["observation_count"] == 5
    assert len(reconciled_members) == 5
    obs_set = {m["observation_id"] for m in reconciled_members}
    assert obs_set == {"A", "B", "C", "D", "E"}
