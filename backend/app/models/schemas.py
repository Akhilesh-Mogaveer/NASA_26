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


# ==========================================
# Phase 4.4 Matching Dashboard Map Schemas
# ==========================================

class MapObservationItem(BaseModel):
    """Observation item tailored for interactive map visualization and filtering."""
    observation_id: str
    sensor: str  # 'MODIS' or 'VIIRS'
    satellite: str
    latitude: float
    longitude: float
    timestamp_utc: str
    frp: float
    confidence: Any  # Sensor-specific: MODIS numeric (0-100) or VIIRS categorical (low/nominal/high)
    status: str  # Primary display status: 'matched', 'unmatched', or 'ambiguous'
    is_ambiguous: bool  # Ambiguity indicator flag
    candidate_count: int  # Degree in candidate association graph
    top_heuristic_score: Optional[float] = None


class MapObservationsResponse(BaseModel):
    """Response containing bounded observations for interactive map rendering."""
    total_count: int
    limit: int
    offset: int
    items: List[MapObservationItem]
    summary_in_bounds: Dict[str, Any]


class MapLineItem(BaseModel):
    """Candidate association vector line connecting a MODIS and VIIRS observation."""
    association_id: str
    modis_observation_id: str
    viirs_observation_id: str
    coordinates: List[List[float]]  # [[modis_lat, modis_lon], [viirs_lat, viirs_lon]]
    distance_km: float
    time_diff_minutes: float
    heuristic_score: float
    classification: str  # 'strong_proximity', 'candidate_association', 'ambiguous_association'
    multiplicity_type: str  # '1:1', '1:N', 'N:1', 'M:N'
    modis_frp: float
    viirs_frp: float


class MapLinesResponse(BaseModel):
    """Response containing bounded candidate association lines."""
    total_count: int
    limit: int
    items: List[MapLineItem]


class ObservationDetailResponse(BaseModel):
    """Detailed observation record and all associated candidate edges."""
    observation_id: str
    sensor: str
    satellite: str
    latitude: float
    longitude: float
    timestamp_utc: str
    frp: float
    confidence: Any
    brightness: Optional[float] = None
    scan: Optional[float] = None
    track: Optional[float] = None
    daynight: Optional[str] = None
    status: str
    is_ambiguous: bool
    candidate_count: int
    associated_candidates: List[Dict[str, Any]] = []


class FilteredMatchingSummaryResponse(BaseModel):
    """Scientifically grounded matching metrics for a filtered region or viewport."""
    total_modis: int
    total_viirs: int
    total_observations: int
    unique_matched_modis: int
    unique_matched_viirs: int
    unique_unmatched_modis: int
    unique_unmatched_viirs: int
    unique_ambiguous_modis: int
    unique_ambiguous_viirs: int
    total_candidate_edges: int
    modis_match_rate_pct: float
    viirs_match_rate_pct: float
    mean_distance_km: float
    mean_time_diff_min: float
    bounds_applied: Optional[Dict[str, Any]] = None
    date_range_applied: Optional[Dict[str, Any]] = None


# ==========================================
# Phase 4.5 Full-Scale Processing Schemas
# ==========================================

class FullScaleJobStartRequest(BaseModel):
    """Parameters for initiating a partitioned full-scale matching job."""
    date_start: Optional[str] = Field(default="2025-08-01", description="Start date YYYY-MM-DD")
    date_end: Optional[str] = Field(default="2025-08-02", description="End date YYYY-MM-DD")
    spatial_radius_km: Optional[float] = Field(default=2.0, ge=0.5, le=10.0)
    temporal_window_minutes: Optional[float] = Field(default=60.0, ge=5.0, le=240.0)
    temporal_halo_minutes: Optional[float] = Field(default=90.0, ge=60.0, le=360.0)
    spatial_tile_deg: Optional[float] = Field(default=None, description="Optional spatial tile size in degrees")
    scale_preset: Optional[str] = Field(default="regional_boreal", description="'regional_boreal', 'multiday_boreal', 'expanded_boreal', 'custom'")
    resume: Optional[bool] = Field(default=True, description="Skip already completed partitions")
    max_partitions: Optional[int] = Field(default=None, description="Maximum partitions to process in this run")


class PartitionProgressItem(BaseModel):
    """Individual partition status in full-scale processing."""
    partition_id: str
    status: str  # 'pending', 'processing', 'completed', 'failed', 'skipped'
    date: str
    bounds: Optional[Dict[str, float]] = None
    modis_count: int = 0
    viirs_count: int = 0
    candidate_count: int = 0
    runtime_seconds: float = 0.0
    output_file: Optional[str] = None
    error_message: Optional[str] = None


class FullScaleJobStatusResponse(BaseModel):
    """Status and progress of full-scale partitioned matching jobs."""
    job_id: str
    status: str  # 'idle', 'running', 'completed', 'failed'
    scale_preset: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    total_partitions: int = 0
    completed_partitions: int = 0
    failed_partitions: int = 0
    current_partition: Optional[str] = None
    progress_pct: float = 0.0
    total_input_observations: int = 0
    total_candidate_edges: int = 0
    unique_matched_modis: int = 0
    unique_matched_viirs: int = 0
    runtime_seconds: float = 0.0
    peak_memory_mb: float = 0.0
    throughput_pairs_per_sec: float = 0.0
    message: Optional[str] = None
    partitions: List[PartitionProgressItem] = []


class FullScaleBenchmarksResponse(BaseModel):
    """Progressive real-data benchmarks across multiple dataset scales."""
    benchmarks: List[Dict[str, Any]]
    methodology_notes: List[str]



