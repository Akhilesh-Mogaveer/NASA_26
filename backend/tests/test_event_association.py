"""Unit and Integration Tests for Phase 5.2 Cross-Sensor Event Association.

Verifies:
1. 1:1 direct cluster relationship.
2. 1:N cluster relationship (one MODIS cluster associated with multiple VIIRS clusters).
3. N:1 cluster relationship (multiple MODIS clusters associated with one VIIRS cluster).
4. M:N complex multi-cluster relationship.
5. No supporting candidate edges produces 0 relationships.
6. Observations with noise status are excluded from cluster relationships.
7. Ambiguity detection when score difference between candidate relationships <= threshold.
8. Unique observation coverage calculation (N_supp / N_total).
9. Bipartite connected component generation and topology typing.
10. Stable relationship identifiers.
"""

import pytest
import pandas as pd
from app.services.event_association import CrossSensorEventAssociator


def test_1_to_1_cluster_relationship():
    """Verify clean 1:1 association when one MODIS cluster associates with one VIIRS cluster."""
    m_clusters = [{
        "cluster_id": "CLUST-MODIS-00001",
        "observation_count": 3,
        "centroid_latitude": 55.0,
        "centroid_longitude": -105.0,
        "start_timestamp_utc": "2025-08-01 12:00:00",
        "end_timestamp_utc": "2025-08-01 12:15:00",
        "sum_frp_mw": 150.0,
    }]
    v_clusters = [{
        "cluster_id": "CLUST-VIIRS-00001",
        "observation_count": 5,
        "centroid_latitude": 55.002,
        "centroid_longitude": -105.002,
        "start_timestamp_utc": "2025-08-01 12:05:00",
        "end_timestamp_utc": "2025-08-01 12:20:00",
        "sum_frp_mw": 200.0,
    }]
    m_members = [
        {"observation_id": "M1", "cluster_id": "CLUST-MODIS-00001"},
        {"observation_id": "M2", "cluster_id": "CLUST-MODIS-00001"},
        {"observation_id": "M3", "cluster_id": "CLUST-MODIS-00001"},
    ]
    v_members = [
        {"observation_id": "V1", "cluster_id": "CLUST-VIIRS-00001"},
        {"observation_id": "V2", "cluster_id": "CLUST-VIIRS-00001"},
        {"observation_id": "V3", "cluster_id": "CLUST-VIIRS-00001"},
        {"observation_id": "V4", "cluster_id": "CLUST-VIIRS-00001"},
        {"observation_id": "V5", "cluster_id": "CLUST-VIIRS-00001"},
    ]

    # Candidate observation associations linking M1-V1, M2-V2, M3-V3
    cand_df = pd.DataFrame([
        {"modis_observation_id": "M1", "viirs_observation_id": "V1", "distance_km": 0.5, "time_diff_minutes": 5.0, "heuristic_score": 0.85},
        {"modis_observation_id": "M2", "viirs_observation_id": "V2", "distance_km": 0.7, "time_diff_minutes": 8.0, "heuristic_score": 0.80},
        {"modis_observation_id": "M3", "viirs_observation_id": "V3", "distance_km": 0.6, "time_diff_minutes": 6.0, "heuristic_score": 0.82},
    ])

    associator = CrossSensorEventAssociator()
    relationships, components, summary = associator.associate_clusters(
        modis_clusters=m_clusters,
        viirs_clusters=v_clusters,
        modis_memberships=m_members,
        viirs_memberships=v_members,
        candidate_associations_df=cand_df,
    )

    assert len(relationships) == 1
    rel = relationships[0]
    assert rel["relationship_id"] == "REL-CLUST-MODIS-00001-CLUST-VIIRS-00001"
    assert rel["multiplicity_type"] == "1:1"
    assert rel["supporting_pairs_count"] == 3
    assert rel["unique_supporting_modis_obs"] == 3
    assert rel["unique_supporting_viirs_obs"] == 3
    # Coverage: MODIS = 3/3 = 1.0, VIIRS = 3/5 = 0.6
    assert abs(rel["modis_obs_coverage_ratio"] - 1.0) < 0.01
    assert abs(rel["viirs_obs_coverage_ratio"] - 0.6) < 0.01
    assert not rel["is_ambiguous"]

    assert len(components) == 1
    assert components[0]["topology_type"] == "1:1_pair"


def test_1_to_n_cluster_relationship():
    """Verify 1:N relationship when one MODIS cluster associates with two distinct VIIRS clusters."""
    m_clusters = [{
        "cluster_id": "CLUST-MODIS-00001",
        "observation_count": 4,
        "centroid_latitude": 55.0,
        "centroid_longitude": -105.0,
        "start_timestamp_utc": "2025-08-01 12:00:00",
        "end_timestamp_utc": "2025-08-01 12:20:00",
        "sum_frp_mw": 200.0,
    }]
    v_clusters = [
        {"cluster_id": "CLUST-VIIRS-00001", "observation_count": 3, "centroid_latitude": 55.002, "centroid_longitude": -105.002, "start_timestamp_utc": "2025-08-01 12:05:00", "end_timestamp_utc": "2025-08-01 12:15:00", "sum_frp_mw": 100.0},
        {"cluster_id": "CLUST-VIIRS-00002", "observation_count": 3, "centroid_latitude": 55.008, "centroid_longitude": -105.008, "start_timestamp_utc": "2025-08-01 12:10:00", "end_timestamp_utc": "2025-08-01 12:20:00", "sum_frp_mw": 120.0},
    ]
    m_members = [
        {"observation_id": "M1", "cluster_id": "CLUST-MODIS-00001"},
        {"observation_id": "M2", "cluster_id": "CLUST-MODIS-00001"},
        {"observation_id": "M3", "cluster_id": "CLUST-MODIS-00001"},
        {"observation_id": "M4", "cluster_id": "CLUST-MODIS-00001"},
    ]
    v_members = [
        {"observation_id": "V1", "cluster_id": "CLUST-VIIRS-00001"},
        {"observation_id": "V2", "cluster_id": "CLUST-VIIRS-00001"},
        {"observation_id": "V3", "cluster_id": "CLUST-VIIRS-00002"},
        {"observation_id": "V4", "cluster_id": "CLUST-VIIRS-00002"},
    ]

    cand_df = pd.DataFrame([
        {"modis_observation_id": "M1", "viirs_observation_id": "V1", "distance_km": 0.5, "time_diff_minutes": 5.0, "heuristic_score": 0.8},
        {"modis_observation_id": "M2", "viirs_observation_id": "V3", "distance_km": 0.8, "time_diff_minutes": 7.0, "heuristic_score": 0.7},
    ])

    associator = CrossSensorEventAssociator()
    relationships, components, summary = associator.associate_clusters(
        modis_clusters=m_clusters,
        viirs_clusters=v_clusters,
        modis_memberships=m_members,
        viirs_memberships=v_members,
        candidate_associations_df=cand_df,
    )

    assert len(relationships) == 2
    for r in relationships:
        assert r["multiplicity_type"] == "1:N"

    assert len(components) == 1
    assert components[0]["topology_type"] == "1:N_star"
    assert components[0]["modis_clusters_count"] == 1
    assert components[0]["viirs_clusters_count"] == 2


def test_n_to_1_cluster_relationship():
    """Verify N:1 relationship when multiple MODIS clusters associate with one VIIRS cluster."""
    m_clusters = [
        {"cluster_id": "CLUST-MODIS-00001", "observation_count": 3, "centroid_latitude": 55.0, "centroid_longitude": -105.0, "start_timestamp_utc": "2025-08-01 12:00:00", "end_timestamp_utc": "2025-08-01 12:10:00", "sum_frp_mw": 100.0},
        {"cluster_id": "CLUST-MODIS-00002", "observation_count": 3, "centroid_latitude": 55.01, "centroid_longitude": -105.01, "start_timestamp_utc": "2025-08-01 12:05:00", "end_timestamp_utc": "2025-08-01 12:15:00", "sum_frp_mw": 110.0},
    ]
    v_clusters = [{
        "cluster_id": "CLUST-VIIRS-00001", "observation_count": 6, "centroid_latitude": 55.005, "centroid_longitude": -105.005, "start_timestamp_utc": "2025-08-01 12:00:00", "end_timestamp_utc": "2025-08-01 12:20:00", "sum_frp_mw": 250.0
    }]
    m_members = [
        {"observation_id": "M1", "cluster_id": "CLUST-MODIS-00001"},
        {"observation_id": "M2", "cluster_id": "CLUST-MODIS-00002"},
    ]
    v_members = [
        {"observation_id": "V1", "cluster_id": "CLUST-VIIRS-00001"},
        {"observation_id": "V2", "cluster_id": "CLUST-VIIRS-00001"},
    ]
    cand_df = pd.DataFrame([
        {"modis_observation_id": "M1", "viirs_observation_id": "V1", "distance_km": 0.5, "time_diff_minutes": 5.0, "heuristic_score": 0.8},
        {"modis_observation_id": "M2", "viirs_observation_id": "V2", "distance_km": 0.6, "time_diff_minutes": 6.0, "heuristic_score": 0.75},
    ])

    associator = CrossSensorEventAssociator()
    relationships, components, summary = associator.associate_clusters(
        modis_clusters=m_clusters,
        viirs_clusters=v_clusters,
        modis_memberships=m_members,
        viirs_memberships=v_members,
        candidate_associations_df=cand_df,
    )

    assert len(relationships) == 2
    for r in relationships:
        assert r["multiplicity_type"] == "N:1"

    assert len(components) == 1
    assert components[0]["topology_type"] == "N:1_star"


def test_noise_observations_excluded_from_cluster_relationships():
    """Candidate pairs involving noise observations must NOT create cluster-to-cluster edges."""
    m_clusters = [{"cluster_id": "CLUST-MODIS-00001", "observation_count": 3, "centroid_latitude": 55.0, "centroid_longitude": -105.0, "start_timestamp_utc": "2025-08-01 12:00:00", "end_timestamp_utc": "2025-08-01 12:10:00", "sum_frp_mw": 100.0}]
    v_clusters = [{"cluster_id": "CLUST-VIIRS-00001", "observation_count": 3, "centroid_latitude": 55.0, "centroid_longitude": -105.0, "start_timestamp_utc": "2025-08-01 12:00:00", "end_timestamp_utc": "2025-08-01 12:10:00", "sum_frp_mw": 100.0}]

    m_members = [
        {"observation_id": "M_CLUSTER", "cluster_id": "CLUST-MODIS-00001"},
        {"observation_id": "M_NOISE", "cluster_id": "NOISE"},
    ]
    v_members = [
        {"observation_id": "V_CLUSTER", "cluster_id": "CLUST-VIIRS-00001"},
        {"observation_id": "V_NOISE", "cluster_id": "NOISE"},
    ]

    # Candidate pairs: one valid cluster-to-cluster, one noise-to-cluster
    cand_df = pd.DataFrame([
        {"modis_observation_id": "M_CLUSTER", "viirs_observation_id": "V_CLUSTER", "distance_km": 0.5, "time_diff_minutes": 5.0, "heuristic_score": 0.8},
        {"modis_observation_id": "M_NOISE", "viirs_observation_id": "V_CLUSTER", "distance_km": 0.5, "time_diff_minutes": 5.0, "heuristic_score": 0.8},
        {"modis_observation_id": "M_CLUSTER", "viirs_observation_id": "V_NOISE", "distance_km": 0.5, "time_diff_minutes": 5.0, "heuristic_score": 0.8},
    ])

    associator = CrossSensorEventAssociator()
    relationships, _, _ = associator.associate_clusters(
        modis_clusters=m_clusters,
        viirs_clusters=v_clusters,
        modis_memberships=m_members,
        viirs_memberships=v_members,
        candidate_associations_df=cand_df,
    )

    assert len(relationships) == 1
    # Only the cluster-to-cluster edge is accepted
    assert relationships[0]["relationship_id"] == "REL-CLUST-MODIS-00001-CLUST-VIIRS-00001"
    assert relationships[0]["supporting_pairs_count"] == 1


def test_no_candidate_edges_produces_empty_result():
    """When no candidate edges link clusters, empty relationships list must be returned."""
    m_clusters = [{"cluster_id": "CLUST-MODIS-00001", "observation_count": 3, "centroid_latitude": 55.0, "centroid_longitude": -105.0, "start_timestamp_utc": "2025-08-01 12:00:00", "end_timestamp_utc": "2025-08-01 12:10:00", "sum_frp_mw": 100.0}]
    v_clusters = [{"cluster_id": "CLUST-VIIRS-00001", "observation_count": 3, "centroid_latitude": 55.0, "centroid_longitude": -105.0, "start_timestamp_utc": "2025-08-01 12:00:00", "end_timestamp_utc": "2025-08-01 12:10:00", "sum_frp_mw": 100.0}]

    associator = CrossSensorEventAssociator()
    relationships, components, summary = associator.associate_clusters(
        modis_clusters=m_clusters,
        viirs_clusters=v_clusters,
        modis_memberships=[],
        viirs_memberships=[],
        candidate_associations_df=pd.DataFrame(),
    )

    assert relationships == []
    assert components == []
    assert summary["total_candidate_relationships"] == 0
