"""Spatial-Temporal Candidate Generation Engine for FireLens.

Implements geodesic distance calculations, time-window filtering,
spatial indexing via BallTree (Haversine metric), and heuristic scoring
for MODIS and VIIRS active-fire observations.
"""
import math
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from app.services.matching_config import (
    EARTH_RADIUS_KM,
    MatchingConfig,
)


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on the Earth surface in kilometers.
    
    Correctly accounts for antimeridian crossing (-180 / +180) and high-latitude convergence.
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    
    # Antimeridian wrap-around adjustment
    delta_lambda = math.radians(lon2 - lon1)
    delta_lambda = (delta_lambda + math.pi) % (2.0 * math.pi) - math.pi

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    
    # Clamp to [0, 1] to avoid floating-point errors near antipodes
    a = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_KM * c


def compute_spatial_score(distance_km: float, max_radius_km: float) -> float:
    """Normalized spatial proximity score in [0.0, 1.0].
    
    score = max(0, 1 - distance / radius)
    """
    if max_radius_km <= 0:
        return 0.0
    return max(0.0, 1.0 - (distance_km / max_radius_km))


def compute_temporal_score(time_diff_minutes: float, max_window_minutes: float) -> float:
    """Normalized temporal proximity score in [0.0, 1.0].
    
    score = max(0, 1 - time_difference / window)
    """
    if max_window_minutes <= 0:
        return 0.0
    return max(0.0, 1.0 - (time_diff_minutes / max_window_minutes))


def compute_heuristic_score(
    spatial_score: float,
    temporal_score: float,
    weight_spatial: float = 0.5,
    weight_temporal: float = 0.5,
) -> float:
    """Compute combined heuristic ranking score.
    
    NOTE: This is an empirical proximity ranking score, NOT a calibrated
    probability of physical fire identity.
    """
    return (weight_spatial * spatial_score) + (weight_temporal * temporal_score)


def parse_timestamp_to_epoch(ts: Any) -> Optional[float]:
    """Parse various timestamp representations into Unix epoch seconds.
    
    Handles ISO 8601 strings, pandas Timestamps, and datetime objects.
    """
    if pd.isna(ts) or ts is None or ts == "":
        return None
    if isinstance(ts, (int, float)):
        return float(ts)
    if isinstance(ts, pd.Timestamp):
        return ts.timestamp()
    if isinstance(ts, datetime):
        return ts.timestamp()
    
    # String parsing
    ts_str = str(ts).strip()
    # Normalize ISO format
    ts_str = ts_str.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(ts_str)
        return dt.timestamp()
    except Exception:
        pass
    
    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]:
        try:
            dt = datetime.strptime(ts_str[:19], fmt)
            return dt.timestamp()
        except Exception:
            continue
    return None


class CandidateGenerator:
    """Scalable spatial-temporal candidate generator using BallTree and temporal window indexing."""

    def __init__(self, config: Optional[MatchingConfig] = None):
        self.config = config or MatchingConfig()
        self.config.validate()

    def generate_candidates(
        self,
        modis_df: pd.DataFrame,
        viirs_df: pd.DataFrame,
    ) -> List[Dict[str, Any]]:
        """Generate all candidate pairs satisfying spatial and temporal thresholds.
        
        Preserves all plausible candidate pairs without premature discarding.
        """
        if modis_df.empty or viirs_df.empty:
            return []

        # Make clean working copies
        m_df = modis_df.copy()
        v_df = viirs_df.copy()

        # Apply validity and duplicate filters if configured
        if self.config.valid_only:
            if "is_valid" in m_df.columns:
                m_df = m_df[m_df["is_valid"].astype(str).str.lower().isin(["true", "1"])].copy()
            if "is_valid" in v_df.columns:
                v_df = v_df[v_df["is_valid"].astype(str).str.lower().isin(["true", "1"])].copy()

        if self.config.exclude_duplicates:
            if "is_duplicate" in m_df.columns:
                m_df = m_df[~m_df["is_duplicate"].astype(str).str.lower().isin(["true", "1"])].copy()
            if "is_duplicate" in v_df.columns:
                v_df = v_df[~v_df["is_duplicate"].astype(str).str.lower().isin(["true", "1"])].copy()

        if m_df.empty or v_df.empty:
            return []

        # Ensure epoch timestamps are populated
        if "epoch_seconds" not in m_df.columns:
            m_df["epoch_seconds"] = m_df["timestamp_utc"].apply(parse_timestamp_to_epoch)
        if "epoch_seconds" not in v_df.columns:
            v_df["epoch_seconds"] = v_df["timestamp_utc"].apply(parse_timestamp_to_epoch)

        # Drop unparseable timestamps
        m_df = m_df.dropna(subset=["epoch_seconds", "latitude", "longitude"]).copy()
        v_df = v_df.dropna(subset=["epoch_seconds", "latitude", "longitude"]).copy()

        if m_df.empty or v_df.empty:
            return []

        # Sort VIIRS by epoch for fast temporal slicing
        v_df = v_df.sort_values("epoch_seconds").reset_index(drop=True)
        v_epochs = v_df["epoch_seconds"].to_numpy()

        # Precompute VIIRS radian coordinates
        v_lat_rad = np.radians(v_df["latitude"].to_numpy())
        v_lon_rad = np.radians(v_df["longitude"].to_numpy())
        v_coords_rad = np.column_stack([v_lat_rad, v_lon_rad])

        window_sec = self.config.temporal_window_minutes * 60.0
        max_radius_rad = self.config.spatial_radius_km / EARTH_RADIUS_KM

        candidates: List[Dict[str, Any]] = []

        # For efficient processing, group MODIS observations into temporal slices
        # or iterate over MODIS observations using binary search on VIIRS epochs
        m_records = m_df.to_dict(orient="records")

        # Cache BallTrees for time intervals to optimize bulk execution
        # When querying, slice VIIRS within [t_modis - window_sec, t_modis + window_sec]
        for m in m_records:
            t_m = m["epoch_seconds"]
            t_min = t_m - window_sec
            t_max = t_m + window_sec

            idx_start = np.searchsorted(v_epochs, t_min, side="left")
            idx_end = np.searchsorted(v_epochs, t_max, side="right")

            if idx_start >= idx_end:
                # No VIIRS observations within temporal window
                continue

            # Candidate VIIRS subset within temporal window
            subset_coords = v_coords_rad[idx_start:idx_end]
            
            # Use BallTree if candidate subset is substantial, or direct haversine if small
            m_lat_rad = math.radians(m["latitude"])
            m_lon_rad = math.radians(m["longitude"])
            m_pt = np.array([[m_lat_rad, m_lon_rad]])

            if (idx_end - idx_start) > 20:
                tree = BallTree(subset_coords, metric="haversine")
                indices, distances = tree.query_radius(m_pt, r=max_radius_rad, return_distance=True)
                match_sub_indices = indices[0]
                match_distances_rad = distances[0]
            else:
                # Direct vectorized Haversine for small subsets (<20 items)
                d_lat = subset_coords[:, 0] - m_lat_rad
                d_lon = subset_coords[:, 1] - m_lon_rad
                d_lon = (d_lon + np.pi) % (2.0 * np.pi) - np.pi
                a = np.sin(d_lat / 2.0)**2 + np.cos(m_lat_rad) * np.cos(subset_coords[:, 0]) * np.sin(d_lon / 2.0)**2
                a = np.clip(a, 0.0, 1.0)
                dist_rad = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
                mask = dist_rad <= max_radius_rad
                match_sub_indices = np.where(mask)[0]
                match_distances_rad = dist_rad[mask]

            for sub_idx, dist_rad in zip(match_sub_indices, match_distances_rad):
                v_global_idx = idx_start + sub_idx
                v = v_df.iloc[v_global_idx]

                # Accurate distance in km
                dist_km = dist_rad * EARTH_RADIUS_KM
                # Time difference in minutes
                time_diff_min = abs(v["epoch_seconds"] - t_m) / 60.0

                if dist_km <= self.config.spatial_radius_km and time_diff_min <= self.config.temporal_window_minutes:
                    s_score = compute_spatial_score(dist_km, self.config.spatial_radius_km)
                    t_score = compute_temporal_score(time_diff_min, self.config.temporal_window_minutes)
                    h_score = compute_heuristic_score(
                        s_score,
                        t_score,
                        self.config.weight_spatial,
                        self.config.weight_temporal,
                    )

                    candidates.append({
                        "modis_observation_id": m.get("observation_id", ""),
                        "viirs_observation_id": v.get("observation_id", ""),
                        "modis_timestamp_utc": str(m.get("timestamp_utc", "")),
                        "viirs_timestamp_utc": str(v.get("timestamp_utc", "")),
                        "distance_km": dist_km,
                        "time_diff_minutes": time_diff_min,
                        "spatial_score": s_score,
                        "temporal_score": t_score,
                        "heuristic_score": h_score,
                        "modis_frp": float(m.get("frp", 0.0) or 0.0),
                        "viirs_frp": float(v.get("frp", 0.0) or 0.0),
                        "modis_latitude": float(m.get("latitude", 0.0)),
                        "modis_longitude": float(m.get("longitude", 0.0)),
                        "viirs_latitude": float(v.get("latitude", 0.0)),
                        "viirs_longitude": float(v.get("longitude", 0.0)),
                        "modis_satellite": str(m.get("satellite", "")),
                        "viirs_satellite": str(v.get("satellite", "")),
                        "spatial_radius_km": self.config.spatial_radius_km,
                        "temporal_window_minutes": self.config.temporal_window_minutes,
                    })

        return candidates
