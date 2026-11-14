"""Pydantic schemas and models for FireLens API."""
from datetime import datetime, timezone
from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field


class RootResponse(BaseModel):
    """Root endpoint response model."""
    message: str = "FireLens API is running"
    status: str = "success"
    version: str = "0.1.0"
    docs_url: str = "/docs"


class HealthResponse(BaseModel):
    """System health check response model."""
    status: str = "healthy"
    service: str = "FireLens API"
    version: str = "0.1.0"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data_directories: Dict[str, bool] = Field(default_factory=dict)


# Schemas designed for upcoming phases according to docs/data_dictionary.md & api_design.md

class FireObservation(BaseModel):
    """Normalized active-fire observation schema."""
    observation_id: str
    latitude: float
    longitude: float
    acquisition_date: str
    acquisition_time: str
    satellite: Optional[str] = None
    instrument: str  # MODIS or VIIRS
    confidence: Optional[Union[str, float, int]] = None
    frp: Optional[float] = None
    brightness: Optional[float] = None
    scan: Optional[float] = None
    track: Optional[float] = None
    daynight: Optional[str] = None
    source_file: Optional[str] = None
    processing_status: str = "valid"
    # Harmonization metadata fields (when associated)
    match_group_id: Optional[str] = None
    matched_observation_id: Optional[str] = None
    distance_km: Optional[float] = None
    time_difference_min: Optional[float] = None
    match_status: Optional[str] = None  # matched, unmatched, uncertain


class FireObservationsResponse(BaseModel):
    """Paginated or limited list of fire observations."""
    total: int
    observations: List[FireObservation]


class SensorComparisonResponse(BaseModel):
    """Comparison metrics between MODIS and VIIRS observations."""
    modis_count: int
    viirs_count: int
    matched_count: int
    unmatched_modis: int
    unmatched_viirs: int
    uncertain_count: int = 0
    average_distance_km: Optional[float] = None
    average_time_diff_min: Optional[float] = None


class DailyActivityItem(BaseModel):
    """Daily fire observation count."""
    date: str
    count: int
    modis_count: Optional[int] = 0
    viirs_count: Optional[int] = 0


class ActivityResponse(BaseModel):
    """Activity analytics summary response."""
    daily_activity: List[DailyActivityItem]


class AnomalyItem(BaseModel):
    """Statistical anomaly record in observed fire activity."""
    date: str
    region: str
    observed_count: int
    historical_mean: float
    historical_std: Optional[float] = None
    z_score: float
    status: str
    explanation: str


class AnomalyResponse(BaseModel):
    """List of detected anomalies."""
    anomalies: List[AnomalyItem]
    method: str = "z_score"
    disclaimer: str = (
        "Statistical anomaly detection identifies unusual observation patterns, not a prediction of future fire events."
    )


class DataQualityResponse(BaseModel):
    """Data processing and quality validation summary."""
    total_records: int
    valid_records: int
    invalid_records: int
    duplicate_records: int
    missing_value_records: int
    modis_raw_files: int = 0
    viirs_raw_files: int = 0
    last_processed_at: Optional[str] = None


class DataIngestResponse(BaseModel):
    """Response returned after running ingestion and validation pipeline."""
    status: str
    message: str
    total_records: int
    valid_records: int
    invalid_records: int
    number_of_source_files: int
    report: Dict[str, Any]


class DataStatusResponse(BaseModel):
    """Response showing current ingestion and dataset status."""
    status: str
    message: str
    last_run_at: Optional[str] = None
    has_processed_data: bool
    modis_raw_files: int = 0
    viirs_raw_files: int = 0
    last_summary: Optional[Dict[str, Any]] = None


class DataPreviewResponse(BaseModel):
    """Response containing a slice of normalized active-fire observations."""
    total_available: int
    limit: int
    offset: int
    source_dataset: str
    records: List[Dict[str, Any]]
    message: str


# Phase 3 Analytics Schemas

class AnalyticsOverviewResponse(BaseModel):
    """High-level analytics overview metrics."""
    generated_at: str
    dataset_provenance: str
    temporal_coverage: Dict[str, Any]
    counts: Dict[str, Any]
    frp_aggregates: Dict[str, Any]
    energetics: Optional[Dict[str, Any]] = None  # Deprecated alias for backwards compatibility
    geographical_extent: Dict[str, Any]
    key_findings: List[str]


class TemporalAnalyticsResponse(BaseModel):
    """Temporal activity distribution across months, hours, days of week, and day/night."""
    generated_at: str
    monthly: List[Dict[str, Any]]
    hourly: List[Dict[str, Any]]
    day_of_week: List[Dict[str, Any]]
    day_night: Dict[str, Any]


class FRPAnalyticsResponse(BaseModel):
    """Fire Radiative Power parametric and non-parametric statistics and histogram."""
    generated_at: str
    overall: Dict[str, Any]
    modis: Dict[str, Any]
    viirs: Dict[str, Any]
    histogram: List[Dict[str, Any]]


class GridCellItem(BaseModel):
    """Aggregated 2-degree grid cell density."""
    lat_bin: float
    lon_bin: float
    modis_count: int
    viirs_count: int
    total_count: int
    mean_frp: float
    total_frp: float


class GeographicalAnalyticsResponse(BaseModel):
    """Geographical distribution and top active grid clusters."""
    total_active_cells: int
    top_cells: List[GridCellItem]
    latitudinal_distribution: List[Dict[str, Any]]


class SensorComparisonDetailedResponse(BaseModel):
    """Detailed scientific comparison between MODIS and VIIRS active-fire instruments."""
    generated_at: str
    observations: Dict[str, Any]
    spatial_resolution: Dict[str, Any]
    frp_comparison: Dict[str, Any]
    confidence_distribution: Dict[str, Any]
    day_night_comparison: Dict[str, Any]
    orbital_parameters: Dict[str, Any]
    scientific_reasons_for_divergence: List[str]


# ==========================================
# Phase 4 Matching Engine Schemas
# ==========================================

class MatchingRunRequest(BaseModel):
    """Request parameters for running spatial-temporal matching."""
    spatial_radius_km: float = Field(default=2.0, ge=0.1, le=20.0, description="Spatial search radius in kilometers (e.g. 1.25, 2.0, 3.5)")
    temporal_window_minutes: float = Field(default=60.0, ge=1.0, le=360.0, description="Temporal window in minutes (e.g. 15, 30, 60, 90)")
    weight_spatial: float = Field(default=0.5, ge=0.0, le=1.0, description="Proximity weight for spatial distance")
    weight_temporal: float = Field(default=0.5, ge=0.0, le=1.0, description="Proximity weight for temporal difference")
    region: Optional[str] = Field(default=None, description="Predefined region code or custom bounds")
    min_lat: Optional[float] = None
    max_lat: Optional[float] = None
    min_lon: Optional[float] = None
    max_lon: Optional[float] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    max_records: Optional[int] = Field(default=50000, le=200000)


class MatchingStatusResponse(BaseModel):
    """Status of spatial-temporal matching engine artifacts."""
    status: str
    message: Optional[str] = None
    generated_at: Optional[str] = None
    artifacts_available: bool
    total_associations: Optional[int] = 0
    unique_modis_matched: Optional[int] = 0
    unique_viirs_matched: Optional[int] = 0
    spatial_radius_km: Optional[float] = 2.0
    temporal_window_minutes: Optional[float] = 60.0


class MatchingSummaryResponse(BaseModel):
    """Top-level summary of matching engine results."""
    generated_at: str
    status: str
    parameters: Dict[str, Any]
    input_counts: Dict[str, Any]
    matching_results: Dict[str, Any]
    multiplicity_breakdown: Dict[str, int]
    classification_breakdown: Dict[str, int]
    statistics: Dict[str, Any]
    benchmarks: Dict[str, Any]
    experiment_metadata: Optional[Dict[str, Any]] = None


class AssociationItem(BaseModel):
    """Individual candidate association item."""
    association_id: str
    modis_observation_id: str
    viirs_observation_id: str
    modis_timestamp_utc: Union[str, Any]
    viirs_timestamp_utc: Union[str, Any]
    distance_km: float
    time_diff_minutes: float
    spatial_score: float
    temporal_score: float
    heuristic_score: float
    candidate_rank: int
    classification: str
    multiplicity_type: str
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
    processed_at: Union[str, Any]


class AssociationsPageResponse(BaseModel):
    """Paginated response of candidate associations."""
    total_count: int
    limit: int
    offset: int
    items: List[AssociationItem]


class UnmatchedItem(BaseModel):
    """Individual unmatched observation item."""
    observation_id: str
    latitude: float
    longitude: float
    timestamp_utc: Union[str, Any]
    frp: float
    satellite: str
    instrument: str
    unmatched_instrument: Optional[str] = None


class UnmatchedPageResponse(BaseModel):
    """Paginated response of unmatched observations."""
    total_count: int
    limit: int
    offset: int
    items: List[UnmatchedItem]


class SensitivityParameterRow(BaseModel):
    """Sensitivity evaluation row for one parameter combination."""
    spatial_radius_km: float
    temporal_window_minutes: float
    total_modis_considered: int
    total_viirs_considered: int
    candidate_association_count: int
    unique_modis_matched: int
    unique_viirs_matched: int
    unmatched_modis_count: int
    unmatched_viirs_count: int
    modis_match_rate_pct: float
    viirs_match_rate_pct: float
    ambiguous_modis_count: int
    ambiguous_viirs_count: int
    modis_ambiguity_pct: float
    viirs_ambiguity_pct: float
    one_to_one_count: int
    one_to_many_count: int
    many_to_one_count: int
    many_to_many_count: int
    strong_proximity_count: int
    candidate_association_count_only: int
    ambiguous_association_count: int
    mean_distance_km: float
    median_distance_km: float
    mean_time_diff_min: float
    median_time_diff_min: float
    candidates_per_matched_modis: float
    candidates_per_matched_viirs: float
    mean_heuristic_score: float


class MatchingEvaluationResponse(BaseModel):
    """Sensitivity evaluation matrix across all 12 parameter combinations."""
    total_combinations: int
    spatial_radii_km: List[float]
    temporal_windows_minutes: List[float]
    matrix: List[SensitivityParameterRow]
    scientific_interpretation: str



