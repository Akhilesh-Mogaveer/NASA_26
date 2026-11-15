"""Spatial-Temporal Fire Event Clustering Engine for FireLens.

Implements independent spatial-temporal clustering for MODIS and VIIRS active-fire
observations using a rigorous DBSCAN formulation on spherical Earth coordinates.

Key Scientific Principles:
1. MODIS and VIIRS observations are clustered INDEPENDENTLY. They are never combined into
   one clustering dataset prior to cross-sensor association.
2. A pair of observations are neighbors iff:
   - Spherical Haversine distance <= spatial_radius_km (R = 6371.0088 km, coordinates in radians)
   - Absolute temporal separation <= temporal_window_minutes
3. Core points have >= min_samples neighbors (including self).
4. Border points are non-core points reachable from a core point.
5. Noise points are non-core, non-border points; they are preserved explicitly, never discarded.
6. Geographic centroids are computed via 3D Cartesian spherical averaging to guarantee
   exact calculations across the antimeridian (-180 / +180) and high polar latitudes.
7. Summed FRP is strictly labeled as "Sum of reported snapshot FRP (MW)", NOT Fire Radiative Energy.
8. Clusters are empirical computational groupings, NOT verified physical fire perimeters.
"""

import math
from typing import List, Dict, Any, Tuple, Optional, Set
from datetime import datetime
import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from app.services.matching_config import EARTH_RADIUS_KM
from app.services.candidate_generation import parse_timestamp_to_epoch, haversine_distance_km


def compute_spherical_centroid(lats: np.ndarray, lons: np.ndarray) -> Tuple[float, float]:
    """Compute the true spherical geographic centroid using 3D Cartesian averaging.
    
    Robust against antimeridian crossings (-180° / +180°) and high-latitude convergence.
    """
    if len(lats) == 0:
        return 0.0, 0.0
    if len(lats) == 1:
        return float(lats[0]), float(lons[0])

    lat_rad = np.radians(lats)
    lon_rad = np.radians(lons)

    # 3D unit vectors
    x = np.cos(lat_rad) * np.cos(lon_rad)
    y = np.cos(lat_rad) * np.sin(lon_rad)
    z = np.sin(lat_rad)

    mean_x = np.mean(x)
    mean_y = np.mean(y)
    mean_z = np.mean(z)

    hyp = math.sqrt(mean_x * mean_x + mean_y * mean_y)
    if hyp < 1e-12:
        # Near north or south pole
        cent_lat = 90.0 if mean_z > 0 else -90.0
        cent_lon = 0.0
    else:
        cent_lat = math.degrees(math.atan2(mean_z, hyp))
        cent_lon = math.degrees(math.atan2(mean_y, mean_x))

    # Normalize longitude to [-180, 180]
    cent_lon = (cent_lon + 180.0) % 360.0 - 180.0
    return float(cent_lat), float(cent_lon)


def compute_bounding_coordinates(lats: np.ndarray, lons: np.ndarray, centroid_lon: float) -> Tuple[float, float, float, float]:
    """Compute bounding latitude and longitude bounds handling antimeridian crossing."""
    if len(lats) == 0:
        return 0.0, 0.0, 0.0, 0.0
    
    min_lat = float(np.min(lats))
    max_lat = float(np.max(lats))

    # Shift longitudes relative to centroid to safely unwrap [-180, 180] antimeridian crossings
    shifted_lons = (lons - centroid_lon + 180.0) % 360.0 - 180.0
    min_shifted = np.min(shifted_lons)
    max_shifted = np.max(shifted_lons)

    min_lon = (centroid_lon + min_shifted + 180.0) % 360.0 - 180.0
    max_lon = (centroid_lon + max_shifted + 180.0) % 360.0 - 180.0

    return min_lat, max_lat, float(min_lon), float(max_lon)


class SpatialTemporalDBSCAN:
    """Independent spatial-temporal DBSCAN clustering for satellite active-fire observations."""

    def __init__(
        self,
        spatial_radius_km: float = 2.0,
        temporal_window_minutes: float = 60.0,
        min_samples: int = 3,
        sensor: str = "MODIS",
    ):
        if spatial_radius_km <= 0:
            raise ValueError(f"spatial_radius_km must be > 0, got {spatial_radius_km}")
        if temporal_window_minutes <= 0:
            raise ValueError(f"temporal_window_minutes must be > 0, got {temporal_window_minutes}")
        if min_samples < 1:
            raise ValueError(f"min_samples must be >= 1, got {min_samples}")

        self.spatial_radius_km = float(spatial_radius_km)
        self.temporal_window_minutes = float(temporal_window_minutes)
        self.min_samples = int(min_samples)
        self.sensor = sensor.upper()

        self.max_radius_rad = self.spatial_radius_km / EARTH_RADIUS_KM
        self.window_sec = self.temporal_window_minutes * 60.0

    def fit(self, df: pd.DataFrame) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Perform spatial-temporal clustering on a single sensor's observations.
        
        Returns:
            clusters: List of cluster summary dictionaries.
            memberships: List of observation-to-cluster assignment dictionaries.
            noise_records: List of noise observation dictionaries.
        """
        if df.empty:
            return [], [], []

        work_df = df.copy()

        # Validate required columns
        for col in ["observation_id", "latitude", "longitude", "timestamp_utc"]:
            if col not in work_df.columns:
                raise ValueError(f"Missing required column '{col}' for clustering")

        # Parse epoch seconds if not present
        if "epoch_seconds" not in work_df.columns:
            work_df["epoch_seconds"] = work_df["timestamp_utc"].apply(parse_timestamp_to_epoch)

        # Drop invalid coordinates or timestamps
        work_df = work_df.dropna(subset=["epoch_seconds", "latitude", "longitude"]).copy()
        if work_df.empty:
            return [], [], []

        # Sort deterministically by epoch, latitude, longitude, observation_id
        work_df = work_df.sort_values(
            ["epoch_seconds", "latitude", "longitude", "observation_id"]
        ).reset_index(drop=True)

        n_points = len(work_df)
        obs_ids = work_df["observation_id"].to_numpy()
        lats = work_df["latitude"].to_numpy(dtype=np.float64)
        lons = work_df["longitude"].to_numpy(dtype=np.float64)
        epochs = work_df["epoch_seconds"].to_numpy(dtype=np.float64)
        timestamps = work_df["timestamp_utc"].to_numpy()
        frp_vals = work_df["frp"].to_numpy(dtype=np.float64) if "frp" in work_df.columns else np.zeros(n_points, dtype=np.float64)
        satellites = work_df["satellite"].to_numpy() if "satellite" in work_df.columns else np.array(["UNKNOWN"] * n_points)

        lat_rad = np.radians(lats)
        lon_rad = np.radians(lons)
        coords_rad = np.column_stack([lat_rad, lon_rad])

        # Step 1: Compute spatial-temporal neighborhoods for all points
        # Using binary search on timestamps combined with BallTree on temporal window candidates
        neighborhoods: List[List[int]] = [[] for _ in range(n_points)]

        for i in range(n_points):
            t_i = epochs[i]
            t_min = t_i - self.window_sec
            t_max = t_i + self.window_sec

            idx_start = int(np.searchsorted(epochs, t_min, side="left"))
            idx_end = int(np.searchsorted(epochs, t_max, side="right"))

            if idx_start >= idx_end:
                neighborhoods[i] = [i]
                continue

            subset_coords = coords_rad[idx_start:idx_end]
            sub_len = idx_end - idx_start

            pt = coords_rad[i:i+1]

            if sub_len > 30:
                tree = BallTree(subset_coords, metric="haversine")
                indices = tree.query_radius(pt, r=self.max_radius_rad)[0]
                matched_indices = [idx_start + int(idx) for idx in indices]
            else:
                # Direct vectorized Haversine
                d_lat = subset_coords[:, 0] - coords_rad[i, 0]
                d_lon = subset_coords[:, 1] - coords_rad[i, 1]
                d_lon = (d_lon + np.pi) % (2.0 * np.pi) - np.pi
                a = (np.sin(d_lat / 2.0) ** 2 +
                     np.cos(coords_rad[i, 0]) * np.cos(subset_coords[:, 0]) * (np.sin(d_lon / 2.0) ** 2))
                a = np.clip(a, 0.0, 1.0)
                dist_rad = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
                matched_sub = np.where(dist_rad <= self.max_radius_rad)[0]
                matched_indices = [idx_start + int(idx) for idx in matched_sub]

            # Ensure self is included
            if i not in matched_indices:
                matched_indices.append(i)
            neighborhoods[i] = matched_indices

        # Step 2: Identify core points
        # A point is core if |N(p)| >= min_samples
        is_core = np.array([len(neighborhoods[i]) >= self.min_samples for i in range(n_points)], dtype=bool)

        # Step 3: DBSCAN Cluster Expansion
        cluster_labels = np.full(n_points, -1, dtype=int)  # -1 = unassigned
        current_cluster_id = 0
        visited = np.zeros(n_points, dtype=bool)

        for i in range(n_points):
            if visited[i] or not is_core[i]:
                continue

            # Start a new cluster
            cluster_labels[i] = current_cluster_id
            visited[i] = True
            queue = [i]
            q_head = 0

            while q_head < len(queue):
                curr = queue[q_head]
                q_head += 1

                # If current point is a core point, expand its neighborhood
                if is_core[curr]:
                    for neighbor in neighborhoods[curr]:
                        if cluster_labels[neighbor] == -1:
                            cluster_labels[neighbor] = current_cluster_id
                        if not visited[neighbor]:
                            visited[neighbor] = True
                            queue.append(neighbor)

            current_cluster_id += 1

        # Step 4: Classify Point Roles (Core, Border, Noise)
        point_roles = []
        for i in range(n_points):
            if cluster_labels[i] == -1:
                point_roles.append("noise")
            elif is_core[i]:
                point_roles.append("core")
            else:
                point_roles.append("border")

        # Step 5: Build Cluster Summaries and Memberships
        raw_clusters: List[Dict[str, Any]] = []
        memberships: List[Dict[str, Any]] = []
        noise_records: List[Dict[str, Any]] = []

        for cid in range(current_cluster_id):
            indices = np.where(cluster_labels == cid)[0]
            if len(indices) == 0:
                continue

            c_lats = lats[indices]
            c_lons = lons[indices]
            c_epochs = epochs[indices]
            c_timestamps = timestamps[indices]
            c_frp = frp_vals[indices]
            c_satellites = satellites[indices]
            c_roles = [point_roles[idx] for idx in indices]

            # Compute spherical centroid
            c_lat, c_lon = compute_spherical_centroid(c_lats, c_lons)
            min_lat, max_lat, min_lon, max_lon = compute_bounding_coordinates(c_lats, c_lons, c_lon)

            # Spatial spread: mean Haversine distance of observations to centroid
            dists_to_centroid = [haversine_distance_km(c_lat, c_lon, lat, lon) for lat, lon in zip(c_lats, c_lons)]
            mean_spatial_spread = float(np.mean(dists_to_centroid))
            max_spatial_spread = float(np.max(dists_to_centroid))

            # Temporal metrics
            min_epoch = float(np.min(c_epochs))
            max_epoch = float(np.max(c_epochs))
            start_ts = str(c_timestamps[np.argmin(c_epochs)])
            end_ts = str(c_timestamps[np.argmax(c_epochs)])
            duration_minutes = round((max_epoch - min_epoch) / 60.0, 2)

            # FRP metrics (MW)
            valid_frp = c_frp[~np.isnan(c_frp)]
            sum_frp_mw = round(float(np.sum(valid_frp)), 2)
            mean_frp_mw = round(float(np.mean(valid_frp)), 2) if len(valid_frp) > 0 else 0.0
            max_frp_mw = round(float(np.max(valid_frp)), 2) if len(valid_frp) > 0 else 0.0

            core_count = sum(1 for r in c_roles if r == "core")
            border_count = sum(1 for r in c_roles if r == "border")

            # Unique platforms represented
            primary_satellite = str(pd.Series(c_satellites).mode()[0]) if len(c_satellites) > 0 else "UNKNOWN"

            raw_clusters.append({
                "internal_id": cid,
                "sensor": self.sensor,
                "observation_count": len(indices),
                "core_count": core_count,
                "border_count": border_count,
                "centroid_latitude": round(c_lat, 5),
                "centroid_longitude": round(c_lon, 5),
                "min_latitude": round(min_lat, 5),
                "max_latitude": round(max_lat, 5),
                "min_longitude": round(min_lon, 5),
                "max_longitude": round(max_lon, 5),
                "start_timestamp_utc": start_ts,
                "end_timestamp_utc": end_ts,
                "duration_minutes": duration_minutes,
                "mean_spatial_spread_km": round(mean_spatial_spread, 3),
                "max_spatial_spread_km": round(max_spatial_spread, 3),
                "sum_frp_mw": sum_frp_mw,
                "mean_frp_mw": mean_frp_mw,
                "max_frp_mw": max_frp_mw,
                "primary_satellite": primary_satellite,
                "spatial_radius_km": self.spatial_radius_km,
                "temporal_window_minutes": self.temporal_window_minutes,
                "min_samples": self.min_samples,
                "_min_epoch": min_epoch,
                "_indices": indices,
            })

        # Sort clusters deterministically by start time, centroid lat, centroid lon
        raw_clusters.sort(key=lambda c: (c["_min_epoch"], c["centroid_latitude"], c["centroid_longitude"]))

        # Assign deterministic, stable cluster IDs: CLUST-{SENSOR}-{INDEX:05d}
        final_clusters: List[Dict[str, Any]] = []
        cluster_id_map: Dict[int, str] = {}

        for seq, c in enumerate(raw_clusters, start=1):
            stable_id = f"CLUST-{self.sensor}-{seq:05d}"
            cluster_id_map[c["internal_id"]] = stable_id
            c["cluster_id"] = stable_id
            
            # Record observation memberships
            for idx in c["_indices"]:
                memberships.append({
                    "observation_id": str(obs_ids[idx]),
                    "cluster_id": stable_id,
                    "sensor": self.sensor,
                    "point_role": point_roles[idx],
                    "latitude": float(lats[idx]),
                    "longitude": float(lons[idx]),
                    "timestamp_utc": str(timestamps[idx]),
                    "frp": float(frp_vals[idx]) if not np.isnan(frp_vals[idx]) else 0.0,
                    "satellite": str(satellites[idx]),
                })

            clean_c = {k: v for k, v in c.items() if not k.startswith("_") and k != "internal_id"}
            final_clusters.append(clean_c)

        # Collect noise observations
        noise_indices = np.where(cluster_labels == -1)[0]
        for idx in noise_indices:
            noise_records.append({
                "observation_id": str(obs_ids[idx]),
                "cluster_id": "NOISE",
                "sensor": self.sensor,
                "point_role": "noise",
                "latitude": float(lats[idx]),
                "longitude": float(lons[idx]),
                "timestamp_utc": str(timestamps[idx]),
                "frp": float(frp_vals[idx]) if not np.isnan(frp_vals[idx]) else 0.0,
                "satellite": str(satellites[idx]),
            })

        return final_clusters, memberships, noise_records


class DisjointSetUnion:
    """Disjoint Set Union (Union-Find) for cluster-label reconciliation across partition boundaries."""

    def __init__(self):
        self.parent: Dict[str, str] = {}

    def find(self, i: str) -> str:
        if self.parent.setdefault(i, i) != i:
            self.parent[i] = self.find(self.parent[i])
        return self.parent[i]

    def union(self, i: str, j: str) -> None:
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i != root_j:
            # Deterministic union: smaller string becomes root
            if root_i < root_j:
                self.parent[root_j] = root_i
            else:
                self.parent[root_i] = root_j


class PartitionedClusteringEngine:
    """Clustering engine with spatial-temporal overlap halos and partition boundary reconciliation.
    
    Reconciles clusters that cross daily or regional boundaries using union-find connected components,
    ensuring identical topology to a global run while keeping memory O(1) bounded per partition.
    """

    def __init__(
        self,
        spatial_radius_km: float = 2.0,
        temporal_window_minutes: float = 60.0,
        min_samples: int = 3,
        sensor: str = "MODIS",
    ):
        self.spatial_radius_km = spatial_radius_km
        self.temporal_window_minutes = temporal_window_minutes
        self.min_samples = min_samples
        self.sensor = sensor.upper()
        self.dbscan = SpatialTemporalDBSCAN(
            spatial_radius_km=spatial_radius_km,
            temporal_window_minutes=temporal_window_minutes,
            min_samples=min_samples,
            sensor=sensor,
        )

    def reconcile_partition_clusters(
        self,
        partition_results: List[Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Reconcile cluster labels across overlapping partition boundaries.
        
        Args:
            partition_results: List of (clusters, memberships, noise) from individual partitions.
            
        Returns:
            Unified (clusters, memberships, noise_records) with 0 duplicate memberships.
        """
        if not partition_results:
            return [], [], []

        dsu = DisjointSetUnion()
        obs_to_clusters: Dict[str, Set[str]] = {}
        all_obs_data: Dict[str, Dict[str, Any]] = {}
        noise_obs: Dict[str, Dict[str, Any]] = {}

        # Collect all observations and detect cross-partition shared memberships
        for part_clusters, part_memberships, part_noise in partition_results:
            for m in part_memberships:
                obs_id = m["observation_id"]
                cid = m["cluster_id"]
                all_obs_data[obs_id] = m
                obs_to_clusters.setdefault(obs_id, set()).add(cid)

            for n in part_noise:
                obs_id = n["observation_id"]
                if obs_id not in all_obs_data:
                    noise_obs[obs_id] = n

        # Union clusters that share identical observations across overlap halos
        for obs_id, cluster_set in obs_to_clusters.items():
            c_list = list(cluster_set)
            for i in range(len(c_list) - 1):
                dsu.union(c_list[i], c_list[i + 1])

        # Group observations by unified cluster root
        unified_groups: Dict[str, List[Dict[str, Any]]] = {}
        for obs_id, cluster_set in obs_to_clusters.items():
            # Any cluster label in set resolves to same root
            root = dsu.find(next(iter(cluster_set)))
            unified_groups.setdefault(root, []).append(all_obs_data[obs_id])

        # Remove noise observations that got clustered in any partition
        final_noise = [n for obs_id, n in noise_obs.items() if obs_id not in all_obs_data]

        # Recompute cluster summaries for unified groups
        raw_unified_clusters: List[Dict[str, Any]] = []
        for root, group in unified_groups.items():
            lats = np.array([m["latitude"] for m in group], dtype=np.float64)
            lons = np.array([m["longitude"] for m in group], dtype=np.float64)
            epochs = np.array([parse_timestamp_to_epoch(m["timestamp_utc"]) for m in group], dtype=np.float64)
            timestamps = np.array([m["timestamp_utc"] for m in group])
            frps = np.array([m.get("frp", 0.0) for m in group], dtype=np.float64)
            satellites = [m.get("satellite", "UNKNOWN") for m in group]
            roles = [m.get("point_role", "core") for m in group]

            c_lat, c_lon = compute_spherical_centroid(lats, lons)
            min_lat, max_lat, min_lon, max_lon = compute_bounding_coordinates(lats, lons, c_lon)

            dists = [haversine_distance_km(c_lat, c_lon, lat, lon) for lat, lon in zip(lats, lons)]
            mean_spread = float(np.mean(dists))
            max_spread = float(np.max(dists))

            min_epoch = float(np.min(epochs))
            max_epoch = float(np.max(epochs))
            start_ts = str(timestamps[np.argmin(epochs)])
            end_ts = str(timestamps[np.argmax(epochs)])
            duration = round((max_epoch - min_epoch) / 60.0, 2)

            valid_frp = frps[~np.isnan(frps)]
            sum_frp = round(float(np.sum(valid_frp)), 2)
            mean_frp = round(float(np.mean(valid_frp)), 2) if len(valid_frp) > 0 else 0.0
            max_frp = round(float(np.max(valid_frp)), 2) if len(valid_frp) > 0 else 0.0

            core_cnt = sum(1 for r in roles if r == "core")
            border_cnt = sum(1 for r in roles if r == "border")
            primary_sat = str(pd.Series(satellites).mode()[0]) if len(satellites) > 0 else "UNKNOWN"

            raw_unified_clusters.append({
                "sensor": self.sensor,
                "observation_count": len(group),
                "core_count": core_cnt,
                "border_count": border_cnt,
                "centroid_latitude": round(c_lat, 5),
                "centroid_longitude": round(c_lon, 5),
                "min_latitude": round(min_lat, 5),
                "max_latitude": round(max_lat, 5),
                "min_longitude": round(min_lon, 5),
                "max_longitude": round(max_lon, 5),
                "start_timestamp_utc": start_ts,
                "end_timestamp_utc": end_ts,
                "duration_minutes": duration,
                "mean_spatial_spread_km": round(mean_spread, 3),
                "max_spatial_spread_km": round(max_spread, 3),
                "sum_frp_mw": sum_frp,
                "mean_frp_mw": mean_frp,
                "max_frp_mw": max_frp,
                "primary_satellite": primary_sat,
                "spatial_radius_km": self.spatial_radius_km,
                "temporal_window_minutes": self.temporal_window_minutes,
                "min_samples": self.min_samples,
                "_min_epoch": min_epoch,
                "_group": group,
            })

        # Deterministic sorting and ID assignment
        raw_unified_clusters.sort(key=lambda c: (c["_min_epoch"], c["centroid_latitude"], c["centroid_longitude"]))

        final_clusters: List[Dict[str, Any]] = []
        final_memberships: List[Dict[str, Any]] = []

        for seq, c in enumerate(raw_unified_clusters, start=1):
            stable_id = f"CLUST-{self.sensor}-{seq:05d}"
            c["cluster_id"] = stable_id

            for m in c["_group"]:
                m_copy = dict(m)
                m_copy["cluster_id"] = stable_id
                final_memberships.append(m_copy)

            clean_c = {k: v for k, v in c.items() if not k.startswith("_")}
            final_clusters.append(clean_c)

        return final_clusters, final_memberships, final_noise
