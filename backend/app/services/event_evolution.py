"""Temporal Event Evolution and Lifecycle Tracking Engine for FireLens (Phase 6).

Analyzes how independently detected MODIS and VIIRS active-fire clusters evolve over
successive satellite observations. Constructs directed temporal event graphs, identifies
candidate continuity relationships, detects possible topological splits and merges,
computes observation-based lifecycle metrics, and tracks event lineage.

Key Scientific Principles:
1. MODIS and VIIRS temporal continuities are processed STRICTLY INDEPENDENTLY.
   Cross-sensor relationships are kept as separate supporting evidence overlays,
   never merged into a single sensor-independent physical event.
2. A temporal event track is an empirical candidate continuity structure, NOT
   proof of physical wildfire identity or propagation.
3. Satellite active-fire observations are discrete instantaneous snapshot detections;
   they do not represent physical fire perimeters, burned area, or spread direction.
4. Missing observations in a temporal interval do NOT prove wildfire extinguishment.
5. Snapshot FRP is expressed in Megawatts (MW); summing snapshot values across
   overpasses does NOT compute Fire Radiative Energy (MJ).
6. Great-circle distances are computed using spherical Haversine metric (R = 6371.0088 km)
   on radian coordinates, handling high-latitude convergence and antimeridian crossings.
"""

import math
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional, Set
from datetime import datetime, timezone
import numpy as np
import pandas as pd

from app.services.matching_config import EARTH_RADIUS_KM
from app.services.candidate_generation import parse_timestamp_to_epoch, haversine_distance_km


@dataclass
class EvolutionConfig:
    """Configurable exploratory parameters for temporal cluster continuity."""
    max_temporal_gap_hours: float = 24.0
    max_spatial_distance_km: float = 5.0
    use_extent_aware: bool = True
    ambiguity_delta_threshold: float = 0.15


class TemporalEventEvolutionEngine:
    """Independent temporal continuity, split/merge detection, and track generation engine."""

    def __init__(self, config: Optional[EvolutionConfig] = None):
        self.config = config or EvolutionConfig()
        if self.config.max_temporal_gap_hours <= 0:
            raise ValueError(f"max_temporal_gap_hours must be > 0, got {self.config.max_temporal_gap_hours}")
        if self.config.max_spatial_distance_km <= 0:
            raise ValueError(f"max_spatial_distance_km must be > 0, got {self.config.max_spatial_distance_km}")

    def find_temporal_relationships(
        self,
        clusters: List[Dict[str, Any]],
        sensor: str,
        cross_sensor_associations: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Identify directed candidate continuity relationships between earlier and later clusters of the SAME sensor.
        
        Args:
            clusters: List of cluster dictionaries for a single sensor.
            sensor: Sensor name ('MODIS' or 'VIIRS').
            cross_sensor_associations: Optional Phase 5 cross-sensor relationships for supporting evidence.
            
        Returns:
            List of directed temporal continuity relationship dictionaries.
        """
        sensor = sensor.upper()
        # Filter for valid clusters belonging to this sensor
        valid_clusters = [
            c for c in clusters
            if str(c.get("cluster_id", "")).startswith(f"CLUST-{sensor}")
            and c.get("cluster_id") != "NOISE"
        ]

        if len(valid_clusters) < 2:
            return []

        # Parse epochs for all clusters
        c_epochs = []
        for c in valid_clusters:
            start_ep = parse_timestamp_to_epoch(c["start_timestamp_utc"]) or 0.0
            end_ep = parse_timestamp_to_epoch(c["end_timestamp_utc"]) or start_ep
            c_epochs.append((start_ep, end_ep))

        # Sort clusters deterministically by start_epoch, centroid_lat, centroid_lon, cluster_id
        cluster_data = []
        for idx, c in enumerate(valid_clusters):
            start_ep, end_ep = c_epochs[idx]
            cluster_data.append({
                "cluster": c,
                "cluster_id": c["cluster_id"],
                "start_epoch": start_ep,
                "end_epoch": end_ep,
                "lat": float(c["centroid_latitude"]),
                "lon": float(c["centroid_longitude"]),
                "spread_km": float(c.get("max_spatial_spread_km", 0.0)),
                "frp": float(c.get("sum_frp_mw", 0.0)),
                "obs_count": int(c.get("observation_count", 0)),
                "satellite": str(c.get("primary_satellite", "UNKNOWN")),
            })

        cluster_data.sort(key=lambda d: (d["start_epoch"], d["lat"], d["lon"], d["cluster_id"]))

        n = len(cluster_data)
        start_epochs_arr = np.array([d["start_epoch"] for d in cluster_data], dtype=np.float64)

        max_gap_sec = self.config.max_temporal_gap_hours * 3600.0

        # Build cross-sensor evidence lookup: cluster_id -> set of counterpart cluster IDs
        cross_sensor_evidence_map: Dict[str, Set[str]] = {}
        if cross_sensor_associations:
            for r in cross_sensor_associations:
                m_cid = r.get("modis_cluster_id")
                v_cid = r.get("viirs_cluster_id")
                if sensor == "MODIS" and m_cid:
                    cross_sensor_evidence_map.setdefault(m_cid, set()).add(v_cid)
                elif sensor == "VIIRS" and v_cid:
                    cross_sensor_evidence_map.setdefault(v_cid, set()).add(m_cid)

        raw_relationships: List[Dict[str, Any]] = []

        # Candidate discovery using temporal indexing and spherical Haversine filtering
        for i in range(n):
            c_i = cluster_data[i]
            t_start_i = c_i["start_epoch"]
            t_end_i = c_i["end_epoch"]

            # Subsequent clusters must have start_epoch > t_start_i (strictly chronologically forward)
            # and within max_gap_sec from t_start_i
            t_search_max = t_start_i + max_gap_sec

            # Binary search for temporal candidate window
            idx_start = int(np.searchsorted(start_epochs_arr, t_start_i, side="right"))
            idx_end = int(np.searchsorted(start_epochs_arr, t_search_max, side="right"))

            if idx_start >= idx_end:
                continue

            for j in range(idx_start, idx_end):
                c_j = cluster_data[j]

                # Self-link rejection
                if c_i["cluster_id"] == c_j["cluster_id"]:
                    continue

                # Reverse-time and simultaneous link rejection: must be strictly later
                if c_j["start_epoch"] <= c_i["start_epoch"]:
                    continue

                # Temporal gap in hours
                # If target starts after source ends: gap between end of source and start of target
                if c_j["start_epoch"] >= t_end_i:
                    gap_sec = c_j["start_epoch"] - t_end_i
                else:
                    # Overlapping temporal clusters from different platforms: gap is forward interval
                    gap_sec = c_j["start_epoch"] - t_start_i

                gap_hours = round(gap_sec / 3600.0, 3)

                # Boundary check: 0 < gap_hours <= max_temporal_gap_hours
                if gap_hours <= 0.0 or gap_hours > self.config.max_temporal_gap_hours:
                    continue

                # Spherical Haversine centroid distance
                dist_centroid = haversine_distance_km(
                    c_i["lat"], c_i["lon"],
                    c_j["lat"], c_j["lon"],
                )
                dist_centroid = round(dist_centroid, 3)

                # Extent-aware distance (accounting for cluster spread)
                r_i = c_i["spread_km"]
                r_j = c_j["spread_km"]
                effective_dist = max(0.0, dist_centroid - (r_i + r_j))
                effective_dist = round(effective_dist, 3)

                # Spatial filter: centroid distance must be within max_spatial_distance_km
                # (or effective distance if extent-aware is enabled and centroid is slightly beyond)
                if self.config.use_extent_aware:
                    spatial_matched = (dist_centroid <= self.config.max_spatial_distance_km) or (effective_dist <= self.config.max_spatial_distance_km)
                    method = "extent_aware_haversine"
                else:
                    spatial_matched = (dist_centroid <= self.config.max_spatial_distance_km)
                    method = "centroid_haversine"

                if not spatial_matched:
                    continue

                # Composite Heuristic Temporal Score in [0.0, 1.0]:
                # Components:
                # - Spatial proximity (40%): 1 - dist_centroid / max_spatial_distance
                # - Temporal proximity (35%): 1 - gap_hours / max_temporal_gap
                # - Extent compatibility (15%): 1 - effective_dist / max_spatial_distance
                # - Snapshot FRP compatibility (10%): min(FRP) / max(FRP)
                s_spatial = max(0.0, 1.0 - (dist_centroid / max(1e-6, self.config.max_spatial_distance_km)))
                s_temporal = max(0.0, 1.0 - (gap_hours / max(1e-6, self.config.max_temporal_gap_hours)))
                s_extent = max(0.0, 1.0 - (effective_dist / max(1e-6, self.config.max_spatial_distance_km)))

                frp_i = c_i["frp"]
                frp_j = c_j["frp"]
                if frp_i > 0 and frp_j > 0:
                    s_frp = min(frp_i, frp_j) / max(frp_i, frp_j)
                else:
                    s_frp = 0.5  # Neutral default when FRP is 0

                heuristic_score = round(
                    (0.40 * s_spatial) +
                    (0.35 * s_temporal) +
                    (0.15 * s_extent) +
                    (0.10 * s_frp),
                    4
                )
                heuristic_score = float(np.clip(heuristic_score, 0.0, 1.0))

                # Cross-sensor supporting evidence
                ev_i = cross_sensor_evidence_map.get(c_i["cluster_id"], set())
                ev_j = cross_sensor_evidence_map.get(c_j["cluster_id"], set())
                shared_counterparts = ev_i.intersection(ev_j)
                supporting_cross_sensor_count = len(shared_counterparts)

                rel_id = f"TEMP-{sensor}-{c_i['cluster_id']}-{c_j['cluster_id']}"

                raw_relationships.append({
                    "relationship_id": rel_id,
                    "sensor": sensor,
                    "source_cluster_id": c_i["cluster_id"],
                    "target_cluster_id": c_j["cluster_id"],
                    "source_start_utc": c_i["cluster"]["start_timestamp_utc"],
                    "source_end_utc": c_i["cluster"]["end_timestamp_utc"],
                    "target_start_utc": c_j["cluster"]["start_timestamp_utc"],
                    "target_end_utc": c_j["cluster"]["end_timestamp_utc"],
                    "temporal_gap_hours": gap_hours,
                    "centroid_distance_km": dist_centroid,
                    "effective_distance_km": effective_dist,
                    "spatial_association_method": method,
                    "source_observation_count": c_i["obs_count"],
                    "target_observation_count": c_j["obs_count"],
                    "source_sum_frp_mw": round(frp_i, 2),
                    "target_sum_frp_mw": round(frp_j, 2),
                    "delta_sum_frp_mw": round(frp_j - frp_i, 2),
                    "source_centroid_lat": c_i["lat"],
                    "source_centroid_lon": c_i["lon"],
                    "target_centroid_lat": c_j["lat"],
                    "target_centroid_lon": c_j["lon"],
                    "heuristic_score": heuristic_score,
                    "supporting_cross_sensor_count": supporting_cross_sensor_count,
                    "_src_epoch": c_i["start_epoch"],
                    "_tgt_epoch": c_j["start_epoch"],
                })

        if not raw_relationships:
            return []

        # Graph degrees: in-degrees (predecessors) and out-degrees (successors)
        out_degrees: Dict[str, int] = {}
        in_degrees: Dict[str, int] = {}
        src_scores: Dict[str, List[float]] = {}
        tgt_scores: Dict[str, List[float]] = {}

        for r in raw_relationships:
            src = r["source_cluster_id"]
            tgt = r["target_cluster_id"]
            out_degrees[src] = out_degrees.get(src, 0) + 1
            in_degrees[tgt] = in_degrees.get(tgt, 0) + 1
            src_scores.setdefault(src, []).append(r["heuristic_score"])
            tgt_scores.setdefault(tgt, []).append(r["heuristic_score"])

        # Topological split/merge classification & ambiguity detection
        for r in raw_relationships:
            src = r["source_cluster_id"]
            tgt = r["target_cluster_id"]
            d_out = out_degrees[src]
            d_in = in_degrees[tgt]

            if d_out == 1 and d_in == 1:
                r["classification"] = "continuation_candidate"
            elif d_out > 1 and d_in == 1:
                r["classification"] = "possible_split"
            elif d_out == 1 and d_in > 1:
                r["classification"] = "possible_merge"
            else:
                r["classification"] = "complex_lineage"

            # Ambiguity: competing successor edges from source or competing predecessor edges into target
            s_scores = sorted(src_scores[src], reverse=True)
            t_scores = sorted(tgt_scores[tgt], reverse=True)

            ambig_src = len(s_scores) > 1 and (s_scores[0] - s_scores[1]) <= self.config.ambiguity_delta_threshold
            ambig_tgt = len(t_scores) > 1 and (t_scores[0] - t_scores[1]) <= self.config.ambiguity_delta_threshold

            r["is_ambiguous"] = ambig_src or ambig_tgt

        # Sort relationships deterministically by source epoch, target epoch, relationship_id
        raw_relationships.sort(key=lambda r: (r["_src_epoch"], r["_tgt_epoch"], r["relationship_id"]))

        # Clean private keys
        cleaned_relationships = [
            {k: v for k, v in r.items() if not k.startswith("_")}
            for r in raw_relationships
        ]

        return cleaned_relationships

    def build_event_tracks(
        self,
        clusters: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        sensor: str,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Construct weakly connected components (event tracks), memberships, and lineage records.
        
        Args:
            clusters: List of valid clusters for this sensor.
            relationships: List of directed temporal relationships.
            sensor: Sensor name ('MODIS' or 'VIIRS').
            
        Returns:
            tracks: List of temporal event track summary dictionaries.
            memberships: List of cluster-to-track assignment dictionaries.
            lineage: List of directed transition dictionaries.
        """
        sensor = sensor.upper()
        valid_clusters = [
            c for c in clusters
            if str(c.get("cluster_id", "")).startswith(f"CLUST-{sensor}")
            and c.get("cluster_id") != "NOISE"
        ]

        cluster_map = {c["cluster_id"]: c for c in valid_clusters}

        # Build undirected adjacency list for weakly connected components
        adj: Dict[str, Set[str]] = {c["cluster_id"]: set() for c in valid_clusters}
        for r in relationships:
            src = r["source_cluster_id"]
            tgt = r["target_cluster_id"]
            if src in adj and tgt in adj:
                adj[src].add(tgt)
                adj[tgt].add(src)

        visited: Set[str] = set()
        components: List[List[str]] = []

        # Deterministic component discovery: sort cluster IDs by earliest start timestamp
        sorted_cluster_ids = sorted(
            list(adj.keys()),
            key=lambda cid: (
                parse_timestamp_to_epoch(cluster_map[cid]["start_timestamp_utc"]) or 0.0,
                cluster_map[cid]["centroid_latitude"],
                cluster_map[cid]["centroid_longitude"],
                cid,
            )
        )

        for start_cid in sorted_cluster_ids:
            if start_cid in visited:
                continue

            comp: List[str] = []
            queue = [start_cid]
            visited.add(start_cid)

            while queue:
                curr = queue.pop(0)
                comp.append(curr)
                for neighbor in sorted(list(adj.get(curr, []))):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

            # Sort clusters within component chronologically
            comp.sort(key=lambda cid: (
                parse_timestamp_to_epoch(cluster_map[cid]["start_timestamp_utc"]) or 0.0,
                cluster_map[cid]["centroid_latitude"],
                cluster_map[cid]["centroid_longitude"],
                cid,
            ))
            components.append(comp)

        # Sort components deterministically by earliest start timestamp of their first cluster
        components.sort(key=lambda comp: (
            parse_timestamp_to_epoch(cluster_map[comp[0]]["start_timestamp_utc"]) or 0.0,
            cluster_map[comp[0]]["centroid_latitude"],
            cluster_map[comp[0]]["centroid_longitude"],
            comp[0],
        ))

        # Index relationships by (source, target) and by component nodes
        rel_by_endpoints: Dict[Tuple[str, str], Dict[str, Any]] = {
            (r["source_cluster_id"], r["target_cluster_id"]): r for r in relationships
        }

        final_tracks: List[Dict[str, Any]] = []
        memberships: List[Dict[str, Any]] = []
        lineage_records: List[Dict[str, Any]] = []

        track_seq = 1

        for comp in components:
            track_id = f"TRACK-{sensor}-{track_seq:05d}"
            track_seq += 1

            comp_clusters = [cluster_map[cid] for cid in comp]
            comp_set = set(comp)

            # Extract relationships strictly within this component
            comp_rels = [
                r for r in relationships
                if r["source_cluster_id"] in comp_set and r["target_cluster_id"] in comp_set
            ]

            # In/out degrees within this track
            in_deg: Dict[str, int] = {cid: 0 for cid in comp}
            out_deg: Dict[str, int] = {cid: 0 for cid in comp}
            preds: Dict[str, List[str]] = {cid: [] for cid in comp}
            succs: Dict[str, List[str]] = {cid: [] for cid in comp}

            for r in comp_rels:
                src = r["source_cluster_id"]
                tgt = r["target_cluster_id"]
                out_deg[src] += 1
                in_deg[tgt] += 1
                preds[tgt].append(src)
                succs[src].append(tgt)
                r["track_id"] = track_id

            # Determine track topology type
            n_clusters = len(comp)
            n_edges = len(comp_rels)
            splits_count = sum(1 for cid in comp if out_deg[cid] > 1)
            merges_count = sum(1 for cid in comp if in_deg[cid] > 1)

            if n_clusters == 1:
                track_type = "isolated_cluster"
            elif splits_count == 0 and merges_count == 0:
                track_type = "linear_track"
            elif splits_count > 0 and merges_count == 0:
                track_type = "branching_split"
            elif splits_count == 0 and merges_count > 0:
                track_type = "branching_merge"
            else:
                track_type = "complex_network"

            # Temporal metrics
            first_ts = comp_clusters[0]["start_timestamp_utc"]
            last_ts = comp_clusters[-1]["end_timestamp_utc"]
            first_ep = parse_timestamp_to_epoch(first_ts) or 0.0
            last_ep = parse_timestamp_to_epoch(last_ts) or first_ep
            total_duration_hours = round(max(0.0, (last_ep - first_ep) / 3600.0), 2)

            # Gaps and separations across linked edges
            if comp_rels:
                gaps = [r["temporal_gap_hours"] for r in comp_rels]
                dists = [r["centroid_distance_km"] for r in comp_rels]
                scores = [r["heuristic_score"] for r in comp_rels]
                mean_gap = round(float(np.mean(gaps)), 2)
                max_gap = round(float(np.max(gaps)), 2)
                mean_dist = round(float(np.mean(dists)), 3)
                max_dist = round(float(np.max(dists)), 3)
                mean_score = round(float(np.mean(scores)), 4)
                has_ambiguity = any(r.get("is_ambiguous", False) for r in comp_rels)
                cross_sensor_assocs_count = sum(r.get("supporting_cross_sensor_count", 0) for r in comp_rels)
            else:
                mean_gap = 0.0
                max_gap = 0.0
                mean_dist = 0.0
                max_dist = 0.0
                mean_score = 0.0
                has_ambiguity = False
                cross_sensor_assocs_count = 0

            # FRP and observation totals
            obs_counts = [int(c.get("observation_count", 0)) for c in comp_clusters]
            total_observations = sum(obs_counts)
            frp_vals = [float(c.get("sum_frp_mw", 0.0)) for c in comp_clusters]
            valid_frp = [f for f in frp_vals if not np.isnan(f)]

            sum_snapshot_frp_mw = round(float(np.sum(valid_frp)), 2)
            mean_frp_mw = round(float(np.mean(valid_frp)), 2) if valid_frp else 0.0
            max_frp_mw = round(float(np.max(valid_frp)), 2) if valid_frp else 0.0
            min_frp_mw = round(float(np.min(valid_frp)), 2) if valid_frp else 0.0

            final_tracks.append({
                "track_id": track_id,
                "sensor": sensor,
                "cluster_count": n_clusters,
                "observation_count": total_observations,
                "temporal_edges_count": n_edges,
                "track_type": track_type,
                "first_observed_utc": first_ts,
                "last_observed_utc": last_ts,
                "total_duration_hours": total_duration_hours,
                "mean_temporal_gap_hours": mean_gap,
                "max_temporal_gap_hours": max_gap,
                "mean_centroid_separation_km": mean_dist,
                "max_centroid_separation_km": max_dist,
                "sum_snapshot_frp_mw": sum_snapshot_frp_mw,
                "mean_frp_mw": mean_frp_mw,
                "max_frp_mw": max_frp_mw,
                "min_frp_mw": min_frp_mw,
                "splits_count": splits_count,
                "merges_count": merges_count,
                "mean_heuristic_score": mean_score,
                "has_ambiguity": has_ambiguity,
                "cross_sensor_associations_count": cross_sensor_assocs_count,
            })

            # Record cluster memberships
            for step_idx, c in enumerate(comp_clusters, start=1):
                cid = c["cluster_id"]
                memberships.append({
                    "track_id": track_id,
                    "cluster_id": cid,
                    "sensor": sensor,
                    "step_index": step_idx,
                    "timestamp_utc": c["start_timestamp_utc"],
                    "observation_count": int(c.get("observation_count", 0)),
                    "centroid_latitude": float(c["centroid_latitude"]),
                    "centroid_longitude": float(c["centroid_longitude"]),
                    "sum_frp_mw": float(c.get("sum_frp_mw", 0.0)),
                    "primary_satellite": str(c.get("primary_satellite", "UNKNOWN")),
                    "in_degree": in_deg[cid],
                    "out_degree": out_deg[cid],
                    "predecessors": ",".join(preds[cid]),
                    "successors": ",".join(succs[cid]),
                })

            # Record lineage edges
            for r in comp_rels:
                lineage_records.append({
                    "track_id": track_id,
                    "sensor": sensor,
                    "relationship_id": r["relationship_id"],
                    "source_cluster_id": r["source_cluster_id"],
                    "target_cluster_id": r["target_cluster_id"],
                    "temporal_gap_hours": r["temporal_gap_hours"],
                    "centroid_distance_km": r["centroid_distance_km"],
                    "classification": r["classification"],
                    "heuristic_score": r["heuristic_score"],
                    "is_ambiguous": r["is_ambiguous"],
                })

        return final_tracks, memberships, lineage_records
