"""Cross-Sensor Event Association Engine for FireLens.

Associates independently generated MODIS and VIIRS fire event clusters using supporting
evidence from Phase 4 candidate observation associations.

Key Scientific Principles:
1. Reuses existing Phase 4 candidate associations. Does NOT rerun global all-pairs matching.
2. Uses actual observation-to-cluster membership lookups.
3. Noise observations are excluded from cluster-to-cluster evidence edges.
4. Bipartite graph representation: MODIS clusters on one side, VIIRS clusters on the other.
5. Multiplicity (1:1, 1:N, N:1, M:N) describes graph connectivity topology, NOT physical fire splitting or merging.
6. Heuristic event score is an empirical ranking metric, NOT a calibrated probability.
7. Candidate cluster relationships represent empirical proximity links, NOT proven identical fires.
"""

import math
from typing import List, Dict, Any, Tuple, Optional, Set
from datetime import datetime, timezone
import numpy as np
import pandas as pd

from app.services.matching_config import EARTH_RADIUS_KM
from app.services.candidate_generation import parse_timestamp_to_epoch, haversine_distance_km


class CrossSensorEventAssociator:
    """Associates independently clustered MODIS and VIIRS event groups using observation-level candidate associations."""

    def __init__(
        self,
        spatial_radius_km: float = 2.0,
        temporal_window_minutes: float = 60.0,
        min_supporting_pairs: int = 1,
        ambiguity_delta_threshold: float = 0.15,
    ):
        self.spatial_radius_km = spatial_radius_km
        self.temporal_window_minutes = temporal_window_minutes
        self.min_supporting_pairs = min_supporting_pairs
        self.ambiguity_delta_threshold = ambiguity_delta_threshold

    def associate_clusters(
        self,
        modis_clusters: List[Dict[str, Any]],
        viirs_clusters: List[Dict[str, Any]],
        modis_memberships: List[Dict[str, Any]],
        viirs_memberships: List[Dict[str, Any]],
        candidate_associations_df: pd.DataFrame,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
        """Associate MODIS and VIIRS clusters using Phase 4 candidate associations.
        
        Returns:
            relationships: List of cluster-to-cluster candidate relationship dictionaries.
            components: List of connected component dictionaries.
            summary: Overall cross-sensor event association summary statistics.
        """
        if not modis_clusters or not viirs_clusters or candidate_associations_df.empty:
            empty_summary = self._build_empty_summary(len(modis_clusters), len(viirs_clusters))
            return [], [], empty_summary

        # Build fast cluster metadata lookups
        modis_cluster_map = {c["cluster_id"]: c for c in modis_clusters}
        viirs_cluster_map = {c["cluster_id"]: c for c in viirs_clusters}

        # Build observation-to-cluster lookups (excluding noise)
        m_obs_to_cluster = {
            str(m["observation_id"]): str(m["cluster_id"])
            for m in modis_memberships
            if str(m.get("cluster_id", "")).startswith("CLUST-")
        }
        v_obs_to_cluster = {
            str(v["observation_id"]): str(v["cluster_id"])
            for v in viirs_memberships
            if str(v.get("cluster_id", "")).startswith("CLUST-")
        }

        # Filter candidate associations to pairs where BOTH observations belong to valid non-noise clusters
        cand_df = candidate_associations_df.copy()
        cand_df["modis_obs_str"] = cand_df["modis_observation_id"].astype(str)
        cand_df["viirs_obs_str"] = cand_df["viirs_observation_id"].astype(str)

        cand_df["modis_cluster_id"] = cand_df["modis_obs_str"].map(m_obs_to_cluster)
        cand_df["viirs_cluster_id"] = cand_df["viirs_obs_str"].map(v_obs_to_cluster)

        # Retain only edges with valid cluster assignments on both sides
        valid_edges = cand_df.dropna(subset=["modis_cluster_id", "viirs_cluster_id"]).copy()

        if valid_edges.empty:
            empty_summary = self._build_empty_summary(len(modis_clusters), len(viirs_clusters))
            return [], [], empty_summary

        # Group candidate observation edges by (modis_cluster_id, viirs_cluster_id)
        grouped = valid_edges.groupby(["modis_cluster_id", "viirs_cluster_id"])

        raw_relationships: List[Dict[str, Any]] = []

        for (m_cid, v_cid), group in grouped:
            if len(group) < self.min_supporting_pairs:
                continue

            m_clust = modis_cluster_map.get(m_cid)
            v_clust = viirs_cluster_map.get(v_cid)
            if not m_clust or not v_clust:
                continue

            supporting_pairs_count = len(group)
            unique_m_obs = group["modis_obs_str"].nunique()
            unique_v_obs = group["viirs_obs_str"].nunique()

            m_total_obs = m_clust.get("observation_count", unique_m_obs)
            v_total_obs = v_clust.get("observation_count", unique_v_obs)

            m_coverage_ratio = round(unique_m_obs / max(1, m_total_obs), 4)
            v_coverage_ratio = round(unique_v_obs / max(1, v_total_obs), 4)
            avg_coverage_ratio = round((m_coverage_ratio + v_coverage_ratio) / 2.0, 4)

            # Spatial distance metrics of supporting observation pairs (km)
            dists = group["distance_km"].to_numpy(dtype=float)
            mean_dist = round(float(np.mean(dists)), 3)
            min_dist = round(float(np.min(dists)), 3)
            max_dist = round(float(np.max(dists)), 3)

            # Absolute temporal difference metrics (min)
            time_diffs = group["time_diff_minutes"].to_numpy(dtype=float)
            mean_time_diff = round(float(np.mean(time_diffs)), 2)
            min_time_diff = round(float(np.min(time_diffs)), 2)
            max_time_diff = round(float(np.max(time_diffs)), 2)

            # Observation-level heuristic scores
            h_scores = group["heuristic_score"].to_numpy(dtype=float) if "heuristic_score" in group.columns else np.zeros(len(group))
            mean_h_score = round(float(np.mean(h_scores)), 4)
            max_h_score = round(float(np.max(h_scores)), 4)

            # Distance between cluster geographic centroids
            c_dist = round(haversine_distance_km(
                m_clust["centroid_latitude"], m_clust["centroid_longitude"],
                v_clust["centroid_latitude"], v_clust["centroid_longitude"]
            ), 3)

            # Temporal overlap between cluster bounding intervals
            m_start_sec = parse_timestamp_to_epoch(m_clust["start_timestamp_utc"]) or 0.0
            m_end_sec = parse_timestamp_to_epoch(m_clust["end_timestamp_utc"]) or 0.0
            v_start_sec = parse_timestamp_to_epoch(v_clust["start_timestamp_utc"]) or 0.0
            v_end_sec = parse_timestamp_to_epoch(v_clust["end_timestamp_utc"]) or 0.0

            overlap_start = max(m_start_sec, v_start_sec)
            overlap_end = min(m_end_sec, v_end_sec)
            if overlap_end >= overlap_start:
                temporal_overlap_min = round((overlap_end - overlap_start) / 60.0, 2)
            else:
                # Disjoint: negative temporal gap in minutes
                temporal_overlap_min = round((overlap_end - overlap_start) / 60.0, 2)

            # Normalized Composite Heuristic Event Score in [0.0, 1.0]
            # Components:
            # - Coverage score (35%): fraction of cluster observations linked
            # - Spatial consistency (25%): 1 - mean_dist / spatial_radius
            # - Temporal consistency (20%): 1 - mean_time_diff / temporal_window
            # - Candidate edge heuristic score (20%): mean Phase 4 score
            s_spatial = max(0.0, 1.0 - (mean_dist / max(1e-6, self.spatial_radius_km)))
            s_temporal = max(0.0, 1.0 - (mean_time_diff / max(1e-6, self.temporal_window_minutes)))
            heuristic_event_score = round(
                (0.35 * avg_coverage_ratio) +
                (0.25 * s_spatial) +
                (0.20 * s_temporal) +
                (0.20 * mean_h_score),
                4
            )

            rel_id = f"REL-{m_cid}-{v_cid}"

            raw_relationships.append({
                "relationship_id": rel_id,
                "modis_cluster_id": m_cid,
                "viirs_cluster_id": v_cid,
                "supporting_pairs_count": supporting_pairs_count,
                "unique_supporting_modis_obs": unique_m_obs,
                "unique_supporting_viirs_obs": unique_v_obs,
                "modis_cluster_obs_count": m_total_obs,
                "viirs_cluster_obs_count": v_total_obs,
                "modis_obs_coverage_ratio": m_coverage_ratio,
                "viirs_obs_coverage_ratio": v_coverage_ratio,
                "mean_distance_km": mean_dist,
                "min_distance_km": min_dist,
                "max_distance_km": max_dist,
                "mean_time_diff_minutes": mean_time_diff,
                "min_time_diff_minutes": min_time_diff,
                "max_time_diff_minutes": max_time_diff,
                "mean_heuristic_score": mean_h_score,
                "max_heuristic_score": max_h_score,
                "centroid_distance_km": c_dist,
                "temporal_overlap_minutes": temporal_overlap_min,
                "heuristic_event_score": heuristic_event_score,
                # Centroid coordinates for direct map rendering
                "modis_centroid_lat": m_clust["centroid_latitude"],
                "modis_centroid_lon": m_clust["centroid_longitude"],
                "viirs_centroid_lat": v_clust["centroid_latitude"],
                "viirs_centroid_lon": v_clust["centroid_longitude"],
                "modis_sum_frp_mw": m_clust.get("sum_frp_mw", 0.0),
                "viirs_sum_frp_mw": v_clust.get("sum_frp_mw", 0.0),
            })

        if not raw_relationships:
            empty_summary = self._build_empty_summary(len(modis_clusters), len(viirs_clusters))
            return [], [], empty_summary

        # Step 2: Bipartite Graph Degrees & Multiplicity
        m_degrees: Dict[str, int] = {}
        v_degrees: Dict[str, int] = {}
        for r in raw_relationships:
            m_degrees[r["modis_cluster_id"]] = m_degrees.get(r["modis_cluster_id"], 0) + 1
            v_degrees[r["viirs_cluster_id"]] = v_degrees.get(r["viirs_cluster_id"], 0) + 1

        for r in raw_relationships:
            d_m = m_degrees[r["modis_cluster_id"]]
            d_v = v_degrees[r["viirs_cluster_id"]]
            if d_m == 1 and d_v == 1:
                r["multiplicity_type"] = "1:1"
            elif d_m > 1 and d_v == 1:
                r["multiplicity_type"] = "1:N"
            elif d_m == 1 and d_v > 1:
                r["multiplicity_type"] = "N:1"
            else:
                r["multiplicity_type"] = "M:N"

        # Step 3: Ambiguity Detection & Evidence Classification
        # Check if a cluster associates with multiple counterpart clusters with close scores (delta <= threshold)
        m_rel_scores: Dict[str, List[float]] = {}
        v_rel_scores: Dict[str, List[float]] = {}
        for r in raw_relationships:
            m_rel_scores.setdefault(r["modis_cluster_id"], []).append(r["heuristic_event_score"])
            v_rel_scores.setdefault(r["viirs_cluster_id"], []).append(r["heuristic_event_score"])

        for r in raw_relationships:
            m_scores = sorted(m_rel_scores[r["modis_cluster_id"]], reverse=True)
            v_scores = sorted(v_rel_scores[r["viirs_cluster_id"]], reverse=True)

            is_m_ambiguous = len(m_scores) > 1 and (m_scores[0] - m_scores[1]) <= self.ambiguity_delta_threshold
            is_v_ambiguous = len(v_scores) > 1 and (v_scores[0] - v_scores[1]) <= self.ambiguity_delta_threshold

            is_ambiguous = is_m_ambiguous or is_v_ambiguous
            r["is_ambiguous"] = is_ambiguous

            # Transparent heuristic evidence classification
            score = r["heuristic_event_score"]
            avg_cov = (r["modis_obs_coverage_ratio"] + r["viirs_obs_coverage_ratio"]) / 2.0

            if is_ambiguous:
                r["classification"] = "ambiguous_candidate"
            elif score >= 0.70 and avg_cov >= 0.30:
                r["classification"] = "stronger_candidate"
            elif score >= 0.45:
                r["classification"] = "moderate_candidate"
            else:
                r["classification"] = "weak_candidate"

        # Step 4: Bipartite Connected Component Analysis
        components = self._compute_connected_components(raw_relationships)

        # Step 5: Summary Statistics
        summary = self._build_summary(
            modis_clusters=modis_clusters,
            viirs_clusters=viirs_clusters,
            relationships=raw_relationships,
            components=components,
        )

        return raw_relationships, components, summary

    def _compute_connected_components(self, relationships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify connected components in the bipartite cluster association graph."""
        adj: Dict[str, Set[str]] = {}
        rel_by_node: Dict[str, List[Dict[str, Any]]] = {}

        for r in relationships:
            m_node = f"M:{r['modis_cluster_id']}"
            v_node = f"V:{r['viirs_cluster_id']}"
            adj.setdefault(m_node, set()).add(v_node)
            adj.setdefault(v_node, set()).add(m_node)
            rel_by_node.setdefault(m_node, []).append(r)
            rel_by_node.setdefault(v_node, []).append(r)

        visited: Set[str] = set()
        components: List[Dict[str, Any]] = []
        comp_seq = 1

        # Deterministic component ordering
        all_nodes = sorted(list(adj.keys()))

        for start_node in all_nodes:
            if start_node in visited:
                continue

            comp_nodes: Set[str] = set()
            queue = [start_node]
            visited.add(start_node)

            while queue:
                curr = queue.pop(0)
                comp_nodes.add(curr)
                for neighbor in adj.get(curr, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

            m_clusters = sorted([n.replace("M:", "") for n in comp_nodes if n.startswith("M:")])
            v_clusters = sorted([n.replace("V:", "") for n in comp_nodes if n.startswith("V:")])

            # Gather unique relationships in component
            seen_rels: Dict[str, Dict[str, Any]] = {}
            for node in comp_nodes:
                for r in rel_by_node.get(node, []):
                    seen_rels[r["relationship_id"]] = r

            comp_rels = list(seen_rels.values())
            m_count = len(m_clusters)
            v_count = len(v_clusters)

            if m_count == 1 and v_count == 1:
                topology_type = "1:1_pair"
            elif m_count == 1 and v_count > 1:
                topology_type = "1:N_star"
            elif m_count > 1 and v_count == 1:
                topology_type = "N:1_star"
            else:
                topology_type = "M:N_complex"

            is_comp_ambiguous = any(r.get("is_ambiguous", False) for r in comp_rels)
            total_supp_pairs = sum(r["supporting_pairs_count"] for r in comp_rels)

            comp_id = f"COMP-{comp_seq:05d}"
            # Annotate relationships with their component_id
            for r in comp_rels:
                r["component_id"] = comp_id

            components.append({
                "component_id": comp_id,
                "topology_type": topology_type,
                "modis_clusters_count": m_count,
                "viirs_clusters_count": v_count,
                "relationship_edges_count": len(comp_rels),
                "total_supporting_pairs": total_supp_pairs,
                "is_ambiguous": is_comp_ambiguous,
                "modis_cluster_ids": m_clusters,
                "viirs_cluster_ids": v_clusters,
                "relationship_ids": sorted(list(seen_rels.keys())),
            })
            comp_seq += 1

        return components

    def _build_summary(
        self,
        modis_clusters: List[Dict[str, Any]],
        viirs_clusters: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        components: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build comprehensive summary statistics for cross-sensor event associations."""
        m_total = len(modis_clusters)
        v_total = len(viirs_clusters)

        associated_m_ids = {r["modis_cluster_id"] for r in relationships}
        associated_v_ids = {r["viirs_cluster_id"] for r in relationships}

        m_associated_count = len(associated_m_ids)
        v_associated_count = len(associated_v_ids)

        m_assoc_rate = round((m_associated_count / max(1, m_total)) * 100.0, 2)
        v_assoc_rate = round((v_associated_count / max(1, v_total)) * 100.0, 2)

        # Multiplicity counts
        multiplicity_counts = {"1:1": 0, "1:N": 0, "N:1": 0, "M:N": 0}
        for r in relationships:
            m_type = r.get("multiplicity_type", "M:N")
            multiplicity_counts[m_type] = multiplicity_counts.get(m_type, 0) + 1

        # Classification counts
        classification_counts = {
            "stronger_candidate": 0,
            "moderate_candidate": 0,
            "weak_candidate": 0,
            "ambiguous_candidate": 0,
        }
        for r in relationships:
            cls = r.get("classification", "weak_candidate")
            classification_counts[cls] = classification_counts.get(cls, 0) + 1

        # Component topology counts
        comp_topology_counts = {
            "1:1_pair": 0,
            "1:N_star": 0,
            "N:1_star": 0,
            "M:N_complex": 0,
        }
        for c in components:
            tt = c.get("topology_type", "M:N_complex")
            comp_topology_counts[tt] = comp_topology_counts.get(tt, 0) + 1

        # Mean metrics across relationships
        mean_event_score = round(float(np.mean([r["heuristic_event_score"] for r in relationships])), 4) if relationships else 0.0
        mean_centroid_dist = round(float(np.mean([r["centroid_distance_km"] for r in relationships])), 3) if relationships else 0.0
        mean_supporting_pairs = round(float(np.mean([r["supporting_pairs_count"] for r in relationships])), 2) if relationships else 0.0

        return {
            "modis_clusters_total": m_total,
            "viirs_clusters_total": v_total,
            "modis_clusters_associated": m_associated_count,
            "viirs_clusters_associated": v_associated_count,
            "modis_cluster_association_rate_pct": m_assoc_rate,
            "viirs_cluster_association_rate_pct": v_assoc_rate,
            "total_candidate_relationships": len(relationships),
            "total_connected_components": len(components),
            "multiplicity_breakdown": multiplicity_counts,
            "classification_breakdown": classification_counts,
            "component_topology_breakdown": comp_topology_counts,
            "mean_heuristic_event_score": mean_event_score,
            "mean_centroid_distance_km": mean_centroid_dist,
            "mean_supporting_pairs_per_relationship": mean_supporting_pairs,
            "parameters": {
                "spatial_radius_km": self.spatial_radius_km,
                "temporal_window_minutes": self.temporal_window_minutes,
                "min_supporting_pairs": self.min_supporting_pairs,
                "ambiguity_delta_threshold": self.ambiguity_delta_threshold,
            },
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    def _build_empty_summary(self, m_total: int, v_total: int) -> Dict[str, Any]:
        return {
            "modis_clusters_total": m_total,
            "viirs_clusters_total": v_total,
            "modis_clusters_associated": 0,
            "viirs_clusters_associated": 0,
            "modis_cluster_association_rate_pct": 0.0,
            "viirs_cluster_association_rate_pct": 0.0,
            "total_candidate_relationships": 0,
            "total_connected_components": 0,
            "multiplicity_breakdown": {"1:1": 0, "1:N": 0, "N:1": 0, "M:N": 0},
            "classification_breakdown": {
                "stronger_candidate": 0, "moderate_candidate": 0, "weak_candidate": 0, "ambiguous_candidate": 0
            },
            "component_topology_breakdown": {
                "1:1_pair": 0, "1:N_star": 0, "N:1_star": 0, "M:N_complex": 0
            },
            "mean_heuristic_event_score": 0.0,
            "mean_centroid_distance_km": 0.0,
            "mean_supporting_pairs_per_relationship": 0.0,
            "parameters": {
                "spatial_radius_km": self.spatial_radius_km,
                "temporal_window_minutes": self.temporal_window_minutes,
                "min_supporting_pairs": self.min_supporting_pairs,
                "ambiguity_delta_threshold": self.ambiguity_delta_threshold,
            },
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
