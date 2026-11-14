"""Unit and Integration Tests for FireLens Spatial-Temporal Matching Engine.

Implements controlled synthetic tests covering all 12 edge cases from Part 7:
1. Exact same-location and same-time observations.
2. Nearby observations within both thresholds.
3. Same location but outside temporal threshold.
4. Same time but outside spatial threshold.
5. Multiple VIIRS candidates for one MODIS observation (1:N sub-pixel splitting).
6. Multiple MODIS candidates for one VIIRS observation (N:1 overlap).
7. Invalid observations (`is_valid=False`).
8. Duplicate observations (`is_duplicate=True`).
9. Coordinates near the antimeridian (-180° / +180° wrap-around).
10. High-latitude observations (cosine latitude area convergence).
11. Observations exactly on threshold boundaries.
12. Missing or malformed timestamps.

Also tests API endpoints (/api/matching/*).
"""
import pytest
import math
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.services.matching_config import (
    MatchingConfig,
    EARTH_RADIUS_KM,
    STRONG_PROXIMITY_THRESHOLD,
)
from app.services.candidate_generation import (
    haversine_distance_km,
    compute_spatial_score,
    compute_temporal_score,
    compute_heuristic_score,
    CandidateGenerator,
)
from app.services.association import AssociationProcessor
from app.services.matching_evaluation import MatchingEvaluator
from app.services.matching import execute_matching_workflow


client = TestClient(app)


# =========================================================================
# PART 7: CONTROLLED SYNTHETIC TESTS FOR ALL 12 EDGE CASES
# =========================================================================

def test_haversine_basic_and_accuracy():
    """Verify haversine formula against known analytical distance."""
    # 1 degree of latitude at equator is approx 111.195 km
    dist = haversine_distance_km(0.0, 0.0, 1.0, 0.0)
    assert 111.0 < dist < 111.4
    # Exact same point is 0.0 km
    assert haversine_distance_km(34.5, -118.2, 34.5, -118.2) == 0.0


def test_case_1_exact_same_location_and_time():
    """Edge Case 1: Exact same location and same time (d=0, dt=0, score=1.0)."""
    cfg = MatchingConfig(spatial_radius_km=2.0, temporal_window_minutes=60.0)
    gen = CandidateGenerator(cfg)

    modis_df = pd.DataFrame([{
        "observation_id": "MOD-1",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "timestamp_utc": "2025-08-15T13:30:00Z",
        "frp": 25.0,
        "satellite": "Aqua",
        "instrument": "MODIS",
        "is_valid": True,
        "is_duplicate": False,
    }])
    viirs_df = pd.DataFrame([{
        "observation_id": "VII-1",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "timestamp_utc": "2025-08-15T13:30:00Z",
        "frp": 12.0,
        "satellite": "NOAA-20",
        "instrument": "VIIRS",
        "is_valid": True,
        "is_duplicate": False,
    }])

    candidates = gen.generate_candidates(modis_df, viirs_df)
    assert len(candidates) == 1
    c = candidates[0]
    assert c["distance_km"] == 0.0
    assert c["time_diff_minutes"] == 0.0
    assert c["spatial_score"] == 1.0
    assert c["temporal_score"] == 1.0
    assert c["heuristic_score"] == 1.0

    processor = AssociationProcessor(cfg)
    result = processor.process_associations(candidates, modis_df, viirs_df)
    assert len(result["associations"]) == 1
    a = result["associations"][0]
    assert a.classification == "strong_proximity"
    assert a.multiplicity_type == "1:1"
    assert a.candidate_rank == 1


def test_case_2_nearby_within_both_thresholds():
    """Edge Case 2: Nearby observations within spatial (<2km) and temporal (<60m) thresholds."""
    cfg = MatchingConfig(spatial_radius_km=2.0, temporal_window_minutes=60.0)
    gen = CandidateGenerator(cfg)

    # Offset by ~0.009 deg lat (~1.0 km) and 15 minutes
    modis_df = pd.DataFrame([{
        "observation_id": "MOD-2",
        "latitude": 34.0000,
        "longitude": -118.0000,
        "timestamp_utc": "2025-08-15T13:30:00Z",
        "frp": 30.0,
        "satellite": "Aqua",
        "instrument": "MODIS",
        "is_valid": True,
        "is_duplicate": False,
    }])
    viirs_df = pd.DataFrame([{
        "observation_id": "VII-2",
        "latitude": 34.0090,
        "longitude": -118.0000,
        "timestamp_utc": "2025-08-15T13:45:00Z",
        "frp": 15.0,
        "satellite": "NOAA-20",
        "instrument": "VIIRS",
        "is_valid": True,
        "is_duplicate": False,
    }])

    candidates = gen.generate_candidates(modis_df, viirs_df)
    assert len(candidates) == 1
    c = candidates[0]
    assert 0.9 < c["distance_km"] < 1.1
    assert c["time_diff_minutes"] == 15.0
    assert 0.4 < c["spatial_score"] < 0.6
    assert c["temporal_score"] == 0.75
    assert 0.5 < c["heuristic_score"] < 0.7


def test_case_3_same_location_outside_temporal_threshold():
    """Edge Case 3: Same location but outside temporal window (>60 min) -> zero candidates."""
    cfg = MatchingConfig(spatial_radius_km=2.0, temporal_window_minutes=60.0)
    gen = CandidateGenerator(cfg)

    modis_df = pd.DataFrame([{
        "observation_id": "MOD-3",
        "latitude": 34.0000,
        "longitude": -118.0000,
        "timestamp_utc": "2025-08-15T10:30:00Z",
        "frp": 30.0,
        "satellite": "Terra",
        "instrument": "MODIS",
        "is_valid": True,
        "is_duplicate": False,
    }])
    # 3 hours later (180 min)
    viirs_df = pd.DataFrame([{
        "observation_id": "VII-3",
        "latitude": 34.0000,
        "longitude": -118.0000,
        "timestamp_utc": "2025-08-15T13:30:00Z",
        "frp": 15.0,
        "satellite": "NOAA-20",
        "instrument": "VIIRS",
        "is_valid": True,
        "is_duplicate": False,
    }])

    candidates = gen.generate_candidates(modis_df, viirs_df)
    assert len(candidates) == 0


def test_case_4_same_time_outside_spatial_threshold():
    """Edge Case 4: Same time but outside spatial radius (>2.0 km) -> zero candidates."""
    cfg = MatchingConfig(spatial_radius_km=2.0, temporal_window_minutes=60.0)
    gen = CandidateGenerator(cfg)

    modis_df = pd.DataFrame([{
        "observation_id": "MOD-4",
        "latitude": 34.0000,
        "longitude": -118.0000,
        "timestamp_utc": "2025-08-15T13:30:00Z",
        "frp": 30.0,
        "satellite": "Aqua",
        "instrument": "MODIS",
        "is_valid": True,
        "is_duplicate": False,
    }])
    # Offset by 0.05 deg lat (~5.5 km)
    viirs_df = pd.DataFrame([{
        "observation_id": "VII-4",
        "latitude": 34.0500,
        "longitude": -118.0000,
        "timestamp_utc": "2025-08-15T13:30:00Z",
        "frp": 15.0,
        "satellite": "NOAA-20",
        "instrument": "VIIRS",
        "is_valid": True,
        "is_duplicate": False,
    }])

    candidates = gen.generate_candidates(modis_df, viirs_df)
    assert len(candidates) == 0


def test_case_5_multiple_viirs_candidates_for_one_modis():
    """Edge Case 5: 1 MODIS observation associated with multiple VIIRS observations (1:N splitting)."""
    cfg = MatchingConfig(spatial_radius_km=3.5, temporal_window_minutes=60.0)
    gen = CandidateGenerator(cfg)

    modis_df = pd.DataFrame([{
        "observation_id": "MOD-5",
        "latitude": -10.0000,
        "longitude": -55.0000,
        "timestamp_utc": "2025-08-15T17:30:00Z",
        "frp": 120.0,
        "satellite": "Aqua",
        "instrument": "MODIS",
        "is_valid": True,
        "is_duplicate": False,
    }])
    # 3 sub-pixel VIIRS hot spots within 2 km
    viirs_df = pd.DataFrame([
        {"observation_id": "VII-5A", "latitude": -10.005, "longitude": -55.000, "timestamp_utc": "2025-08-15T17:40:00Z", "frp": 25.0, "satellite": "NOAA-20", "instrument": "VIIRS", "is_valid": True, "is_duplicate": False},
        {"observation_id": "VII-5B", "latitude": -10.010, "longitude": -55.005, "timestamp_utc": "2025-08-15T17:40:00Z", "frp": 40.0, "satellite": "NOAA-20", "instrument": "VIIRS", "is_valid": True, "is_duplicate": False},
        {"observation_id": "VII-5C", "latitude": -9.9950, "longitude": -55.005, "timestamp_utc": "2025-08-15T17:40:00Z", "frp": 18.0, "satellite": "NOAA-20", "instrument": "VIIRS", "is_valid": True, "is_duplicate": False},
    ])

    candidates = gen.generate_candidates(modis_df, viirs_df)
    assert len(candidates) == 3

    processor = AssociationProcessor(cfg)
    result = processor.process_associations(candidates, modis_df, viirs_df)
    assocs = result["associations"]
    assert len(assocs) == 3
    # All are 1:N multiplicity
    for a in assocs:
        assert a.multiplicity_type == "1:N"
    # Ranks must be 1, 2, 3
    ranks = [a.candidate_rank for a in assocs]
    assert sorted(ranks) == [1, 2, 3]


def test_case_6_multiple_modis_candidates_for_one_viirs():
    """Edge Case 6: Multiple MODIS observations associated with 1 VIIRS observation (N:1 overlap)."""
    cfg = MatchingConfig(spatial_radius_km=3.5, temporal_window_minutes=60.0)
    gen = CandidateGenerator(cfg)

    modis_df = pd.DataFrame([
        {"observation_id": "MOD-6A", "latitude": 45.000, "longitude": 10.000, "timestamp_utc": "2025-08-15T12:00:00Z", "frp": 20.0, "satellite": "Aqua", "instrument": "MODIS", "is_valid": True, "is_duplicate": False},
        {"observation_id": "MOD-6B", "latitude": 45.010, "longitude": 10.010, "timestamp_utc": "2025-08-15T12:05:00Z", "frp": 35.0, "satellite": "Aqua", "instrument": "MODIS", "is_valid": True, "is_duplicate": False},
    ])
    viirs_df = pd.DataFrame([{
        "observation_id": "VII-6",
        "latitude": 45.005,
        "longitude": 10.005,
        "timestamp_utc": "2025-08-15T12:02:00Z",
        "frp": 15.0,
        "satellite": "NOAA-20",
        "instrument": "VIIRS",
        "is_valid": True,
        "is_duplicate": False,
    }])

    candidates = gen.generate_candidates(modis_df, viirs_df)
    assert len(candidates) == 2

    processor = AssociationProcessor(cfg)
    result = processor.process_associations(candidates, modis_df, viirs_df)
    assocs = result["associations"]
    assert len(assocs) == 2
    for a in assocs:
        assert a.multiplicity_type == "N:1"


def test_case_7_invalid_observations_excluded():
    """Edge Case 7: Invalid observations (is_valid=False) excluded from primary matching."""
    cfg = MatchingConfig(spatial_radius_km=2.0, temporal_window_minutes=60.0, valid_only=True)
    gen = CandidateGenerator(cfg)

    modis_df = pd.DataFrame([{
        "observation_id": "MOD-7",
        "latitude": 30.0,
        "longitude": 50.0,
        "timestamp_utc": "2025-08-15T12:00:00Z",
        "frp": -5.0,  # Negative FRP invalid
        "satellite": "Aqua",
        "instrument": "MODIS",
        "is_valid": False,
        "is_duplicate": False,
    }])
    viirs_df = pd.DataFrame([{
        "observation_id": "VII-7",
        "latitude": 30.0,
        "longitude": 50.0,
        "timestamp_utc": "2025-08-15T12:00:00Z",
        "frp": 10.0,
        "satellite": "NOAA-20",
        "instrument": "VIIRS",
        "is_valid": True,
        "is_duplicate": False,
    }])

    candidates = gen.generate_candidates(modis_df, viirs_df)
    assert len(candidates) == 0


def test_case_8_duplicate_observations_handled():
    """Edge Case 8: Duplicate observations (is_duplicate=True) excluded from primary matching."""
    cfg = MatchingConfig(spatial_radius_km=2.0, temporal_window_minutes=60.0, exclude_duplicates=True)
    gen = CandidateGenerator(cfg)

    modis_df = pd.DataFrame([{
        "observation_id": "MOD-8",
        "latitude": 30.0,
        "longitude": 50.0,
        "timestamp_utc": "2025-08-15T12:00:00Z",
        "frp": 25.0,
        "satellite": "Aqua",
        "instrument": "MODIS",
        "is_valid": True,
        "is_duplicate": True,  # Flagged duplicate
    }])
    viirs_df = pd.DataFrame([{
        "observation_id": "VII-8",
        "latitude": 30.0,
        "longitude": 50.0,
        "timestamp_utc": "2025-08-15T12:00:00Z",
        "frp": 10.0,
        "satellite": "NOAA-20",
        "instrument": "VIIRS",
        "is_valid": True,
        "is_duplicate": False,
    }])

    candidates = gen.generate_candidates(modis_df, viirs_df)
    assert len(candidates) == 0


def test_case_9_antimeridian_crossing():
    """Edge Case 9: Coordinates near antimeridian (e.g. +179.99° and -179.99°).
    
    Verifies that geodesic calculation measures ~2.2 km across ±180°, NOT 40,000 km.
    """
    # 0.02 degrees of longitude across antimeridian at equator is approx 2.22 km
    dist = haversine_distance_km(0.0, 179.99, 0.0, -179.99)
    assert 2.1 < dist < 2.3

    cfg = MatchingConfig(spatial_radius_km=3.5, temporal_window_minutes=60.0)
    gen = CandidateGenerator(cfg)

    modis_df = pd.DataFrame([{
        "observation_id": "MOD-9",
        "latitude": -16.5000,
        "longitude": 179.9900,  # East of 180
        "timestamp_utc": "2025-08-15T02:00:00Z",
        "frp": 50.0,
        "satellite": "Aqua",
        "instrument": "MODIS",
        "is_valid": True,
        "is_duplicate": False,
    }])
    viirs_df = pd.DataFrame([{
        "observation_id": "VII-9",
        "latitude": -16.5000,
        "longitude": -179.9950,  # West of 180 (dist is ~1.5 km)
        "timestamp_utc": "2025-08-15T02:10:00Z",
        "frp": 20.0,
        "satellite": "NOAA-20",
        "instrument": "VIIRS",
        "is_valid": True,
        "is_duplicate": False,
    }])

    candidates = gen.generate_candidates(modis_df, viirs_df)
    assert len(candidates) == 1
    assert candidates[0]["distance_km"] < 2.0


def test_case_10_high_latitude_observations():
    """Edge Case 10: High-latitude observations (e.g. 65°N in Boreal Forest).
    
    Verifies that longitude spacing shrinks proportionally with cos(lat).
    """
    # At 65°N, cos(65°) = 0.4226. 1 deg lon is approx 47.0 km (not 111 km)
    dist_high_lat = haversine_distance_km(65.0, 100.0, 65.0, 100.04)
    assert 1.5 < dist_high_lat < 2.5

    cfg = MatchingConfig(spatial_radius_km=2.0, temporal_window_minutes=60.0)
    gen = CandidateGenerator(cfg)

    modis_df = pd.DataFrame([{
        "observation_id": "MOD-10",
        "latitude": 65.0000,
        "longitude": 100.0000,
        "timestamp_utc": "2025-08-15T06:00:00Z",
        "frp": 80.0,
        "satellite": "Aqua",
        "instrument": "MODIS",
        "is_valid": True,
        "is_duplicate": False,
    }])
    # Offset by 0.03 deg longitude at 65°N (~1.41 km)
    viirs_df = pd.DataFrame([{
        "observation_id": "VII-10",
        "latitude": 65.0000,
        "longitude": 100.0300,
        "timestamp_utc": "2025-08-15T06:05:00Z",
        "frp": 45.0,
        "satellite": "NOAA-20",
        "instrument": "VIIRS",
        "is_valid": True,
        "is_duplicate": False,
    }])

    candidates = gen.generate_candidates(modis_df, viirs_df)
    assert len(candidates) == 1
    assert candidates[0]["distance_km"] < 2.0


def test_case_11_threshold_boundary_behavior():
    """Edge Case 11: Observations exactly on or near the threshold boundary."""
    radius_km = 2.0
    window_min = 60.0
    cfg = MatchingConfig(spatial_radius_km=radius_km, temporal_window_minutes=window_min)
    gen = CandidateGenerator(cfg)

    # 1.8 km distance and 55 minutes -> inside
    modis_df = pd.DataFrame([{
        "observation_id": "MOD-11",
        "latitude": 0.0,
        "longitude": 0.0,
        "timestamp_utc": "2025-08-15T12:00:00Z",
        "frp": 25.0,
        "satellite": "Aqua",
        "instrument": "MODIS",
        "is_valid": True,
        "is_duplicate": False,
    }])
    viirs_df_inside = pd.DataFrame([{
        "observation_id": "VII-11-IN",
        "latitude": 0.0,
        "longitude": 1.8 / 111.195,  # ~1.8 km
        "timestamp_utc": "2025-08-15T12:55:00Z",  # 55 min
        "frp": 10.0,
        "satellite": "NOAA-20",
        "instrument": "VIIRS",
        "is_valid": True,
        "is_duplicate": False,
    }])
    candidates_in = gen.generate_candidates(modis_df, viirs_df_inside)
    assert len(candidates_in) == 1

    # 2.2 km distance -> outside
    viirs_df_outside = pd.DataFrame([{
        "observation_id": "VII-11-OUT",
        "latitude": 0.0,
        "longitude": 2.2 / 111.195,  # ~2.2 km
        "timestamp_utc": "2025-08-15T12:10:00Z",
        "frp": 10.0,
        "satellite": "NOAA-20",
        "instrument": "VIIRS",
        "is_valid": True,
        "is_duplicate": False,
    }])
    candidates_out = gen.generate_candidates(modis_df, viirs_df_outside)
    assert len(candidates_out) == 0


def test_case_12_missing_or_malformed_timestamps():
    """Edge Case 12: Missing or corrupt timestamps safely handled without crashing."""
    cfg = MatchingConfig(spatial_radius_km=2.0, temporal_window_minutes=60.0)
    gen = CandidateGenerator(cfg)

    modis_df = pd.DataFrame([
        {"observation_id": "MOD-12A", "latitude": 10.0, "longitude": 20.0, "timestamp_utc": "CORRUPT_TIMESTAMP", "frp": 20.0, "satellite": "Aqua", "instrument": "MODIS", "is_valid": True, "is_duplicate": False},
        {"observation_id": "MOD-12B", "latitude": 10.0, "longitude": 20.0, "timestamp_utc": None, "frp": 20.0, "satellite": "Aqua", "instrument": "MODIS", "is_valid": True, "is_duplicate": False},
        {"observation_id": "MOD-12C", "latitude": 10.0, "longitude": 20.0, "timestamp_utc": "2025-08-15T12:00:00Z", "frp": 20.0, "satellite": "Aqua", "instrument": "MODIS", "is_valid": True, "is_duplicate": False},
    ])
    viirs_df = pd.DataFrame([
        {"observation_id": "VII-12", "latitude": 10.005, "longitude": 20.0, "timestamp_utc": "2025-08-15T12:10:00Z", "frp": 15.0, "satellite": "NOAA-20", "instrument": "VIIRS", "is_valid": True, "is_duplicate": False},
    ])

    candidates = gen.generate_candidates(modis_df, viirs_df)
    # Only MOD-12C should match
    assert len(candidates) == 1
    assert candidates[0]["modis_observation_id"] == "MOD-12C"


# =========================================================================
# EVALUATION & SENSITIVITY GRID TESTS
# =========================================================================

def test_evaluator_grid_12_combinations():
    """Verify that evaluator computes all 12 combinations (3 radii x 4 windows)."""
    evaluator = MatchingEvaluator(
        spatial_radii=[1.25, 2.0, 3.5],
        temporal_windows=[15.0, 30.0, 60.0, 90.0],
    )

    modis_df = pd.DataFrame([
        {"observation_id": "M1", "latitude": 35.0, "longitude": -120.0, "timestamp_utc": "2025-08-15T13:30:00Z", "frp": 45.0, "satellite": "Aqua", "instrument": "MODIS", "is_valid": True, "is_duplicate": False},
        {"observation_id": "M2", "latitude": 35.5, "longitude": -120.5, "timestamp_utc": "2025-08-15T13:35:00Z", "frp": 30.0, "satellite": "Aqua", "instrument": "MODIS", "is_valid": True, "is_duplicate": False},
    ])
    viirs_df = pd.DataFrame([
        {"observation_id": "V1", "latitude": 35.01, "longitude": -120.01, "timestamp_utc": "2025-08-15T13:40:00Z", "frp": 15.0, "satellite": "NOAA-20", "instrument": "VIIRS", "is_valid": True, "is_duplicate": False},
        {"observation_id": "V2", "latitude": 35.02, "longitude": -120.02, "timestamp_utc": "2025-08-15T14:15:00Z", "frp": 12.0, "satellite": "NOAA-20", "instrument": "VIIRS", "is_valid": True, "is_duplicate": False},
    ])

    results = evaluator.evaluate_grid(modis_df, viirs_df)
    assert len(results) == 12  # 3 * 4 = 12

    df = evaluator.to_dataframe(results)
    assert len(df) == 12
    assert "candidate_association_count" in df.columns
    assert "modis_ambiguity_pct" in df.columns
    assert "mean_distance_km" in df.columns


# =========================================================================
# MATCHING API ENDPOINT TESTS
# =========================================================================

def test_api_matching_status_endpoint():
    """Test GET /api/matching/status."""
    response = client.get("/api/matching/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "artifacts_available" in data
    assert data["artifacts_available"] is True


def test_api_matching_summary_endpoint():
    """Test GET /api/matching/summary."""
    response = client.get("/api/matching/summary")
    assert response.status_code == 200
    data = response.json()
    assert "matching_results" in data
    assert "multiplicity_breakdown" in data
    assert "classification_breakdown" in data
    assert "benchmarks" in data
    assert data["matching_results"]["total_candidate_associations"] > 0


def test_api_matching_evaluation_endpoint():
    """Test GET /api/matching/evaluation."""
    response = client.get("/api/matching/evaluation")
    assert response.status_code == 200
    data = response.json()
    assert data["total_combinations"] == 12
    assert len(data["matrix"]) == 12
    assert "scientific_interpretation" in data


def test_api_matching_associations_endpoint():
    """Test GET /api/matching/associations with pagination and filters."""
    response = client.get("/api/matching/associations?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] > 0
    assert len(data["items"]) <= 10
    first = data["items"][0]
    assert "association_id" in first
    assert "modis_observation_id" in first
    assert "viirs_observation_id" in first
    assert "distance_km" in first
    assert "time_diff_minutes" in first
    assert "heuristic_score" in first

    # Test filtering by classification
    response_class = client.get("/api/matching/associations?limit=5&classification=ambiguous_association")
    assert response_class.status_code == 200
    class_data = response_class.json()
    for item in class_data["items"]:
        assert item["classification"] == "ambiguous_association"


def test_api_matching_unmatched_endpoint():
    """Test GET /api/matching/unmatched."""
    response = client.get("/api/matching/unmatched?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] > 0
    assert len(data["items"]) <= 10
    first = data["items"][0]
    assert "observation_id" in first
    assert "latitude" in first
    assert "longitude" in first

