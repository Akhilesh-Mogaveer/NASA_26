"""FireLens Matching Engine Configuration and Data Models.

Defines candidate spatial radii, temporal windows, classification boundaries,
and data models for MODIS-VIIRS spatial-temporal associations.

NOTE ON DISTANCE METRIC:
Distances are calculated as spherical great-circle distances via the Haversine formula
assuming a spherical Earth of mean radius R = 6,371.0088 km (IUGG recommendation).
This is explicitly distinguished from an ellipsoidal geodesic distance (e.g. Karney
or Vincenty formulas on the WGS-84 ellipsoid). The spherical great-circle approximation
differs from ellipsoidal geodesic distance by at most ~0.5% at mid-latitudes, which is
well within the satellite geolocation uncertainty and pixel footprint dimensions of
MODIS (1 km nadir, up to 4.8 km scan-edge) and VIIRS (375 m nadir, up to 800 m scan-edge).

NOTE ON MULTIPLICITY PATTERNS:
Multiplicity patterns ('1:1', '1:N', 'N:1', 'M:N') describe topological degree patterns
in the bipartite candidate association graph. They do NOT represent confirmed physical
fire relationships, proven flame splits, or verified perimeter geometries.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone


# Earth mean radius in kilometers (IUGG recommended)
EARTH_RADIUS_KM: float = 6371.0088

# Candidate starting parameter combinations for sensitivity analysis
CANDIDATE_SPATIAL_RADII_KM: List[float] = [1.25, 2.0, 3.5]
CANDIDATE_TEMPORAL_WINDOWS_MINUTES: List[float] = [15.0, 30.0, 60.0, 90.0]

# Default baseline configuration
DEFAULT_SPATIAL_RADIUS_KM: float = 2.0
DEFAULT_TEMPORAL_WINDOW_MINUTES: float = 60.0
DEFAULT_WEIGHT_SPATIAL: float = 0.5
DEFAULT_WEIGHT_TEMPORAL: float = 0.5

# Heuristic classification thresholds
STRONG_PROXIMITY_THRESHOLD: float = 0.70  # spatial_score >= 0.7 AND temporal_score >= 0.7
AMBIGUITY_SCORE_DELTA: float = 0.15       # Top 2 candidates score difference <= 0.15


@dataclass
class MatchingConfig:
    """Configuration parameters for spatial-temporal matching execution."""
    spatial_radius_km: float = DEFAULT_SPATIAL_RADIUS_KM
    temporal_window_minutes: float = DEFAULT_TEMPORAL_WINDOW_MINUTES
    weight_spatial: float = DEFAULT_WEIGHT_SPATIAL
    weight_temporal: float = DEFAULT_WEIGHT_TEMPORAL
    valid_only: bool = True
    exclude_duplicates: bool = True
    min_score_threshold: float = 0.0

    def validate(self) -> None:
        """Validate parameter ranges."""
        if self.spatial_radius_km <= 0:
            raise ValueError(f"Spatial radius must be positive, got {self.spatial_radius_km}")
        if self.temporal_window_minutes <= 0:
            raise ValueError(f"Temporal window must be positive, got {self.temporal_window_minutes}")
        if not (0.0 <= self.weight_spatial <= 1.0):
            raise ValueError(f"Spatial weight must be in [0, 1], got {self.weight_spatial}")
        if not (0.0 <= self.weight_temporal <= 1.0):
            raise ValueError(f"Temporal weight must be in [0, 1], got {self.weight_temporal}")
        total_weight = self.weight_spatial + self.weight_temporal
        if abs(total_weight - 1.0) > 1e-4:
            raise ValueError(f"Weights must sum to 1.0, got {total_weight}")


@dataclass
class AssociationRecord:
    """Individual candidate association between a MODIS and VIIRS observation."""
    association_id: str
    modis_observation_id: str
    viirs_observation_id: str
    modis_timestamp_utc: str
    viirs_timestamp_utc: str
    distance_km: float
    time_diff_minutes: float
    spatial_score: float
    temporal_score: float
    heuristic_score: float
    candidate_rank: int
    classification: str  # 'strong_proximity', 'candidate_association', 'ambiguous_association'
    multiplicity_type: str  # '1:1', '1:N', 'N:1', 'M:N'
    modis_frp: float
    viirs_frp: float
    modis_latitude: float
    modis_longitude: float
    viirs_latitude: float
    viirs_longitude: float
    modis_satellite: str
    viirs_satellite: str
    spatial_radius_km: float
    temporal_window_minutes: float
    processed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))

    def to_dict(self) -> Dict[str, Any]:
        """Convert association record to dictionary."""
        return {
            "association_id": self.association_id,
            "modis_observation_id": self.modis_observation_id,
            "viirs_observation_id": self.viirs_observation_id,
            "modis_timestamp_utc": self.modis_timestamp_utc,
            "viirs_timestamp_utc": self.viirs_timestamp_utc,
            "distance_km": round(self.distance_km, 4),
            "time_diff_minutes": round(self.time_diff_minutes, 2),
            "spatial_score": round(self.spatial_score, 4),
            "temporal_score": round(self.temporal_score, 4),
            "heuristic_score": round(self.heuristic_score, 4),
            "candidate_rank": self.candidate_rank,
            "classification": self.classification,
            "multiplicity_type": self.multiplicity_type,
            "modis_frp": round(self.modis_frp, 2),
            "viirs_frp": round(self.viirs_frp, 2),
            "modis_latitude": round(self.modis_latitude, 5),
            "modis_longitude": round(self.modis_longitude, 5),
            "viirs_latitude": round(self.viirs_latitude, 5),
            "viirs_longitude": round(self.viirs_longitude, 5),
            "modis_satellite": self.modis_satellite,
            "viirs_satellite": self.viirs_satellite,
            "spatial_radius_km": self.spatial_radius_km,
            "temporal_window_minutes": self.temporal_window_minutes,
            "processed_at": self.processed_at,
        }
