"""Spatial-Temporal Matching Engine API Routes for FireLens.

Exposes endpoints for running matching workflows, retrieving matching summaries,
inspecting paginated candidate associations, viewing unmatched observations,
and analyzing sensitivity evaluations across the 12 candidate parameter combinations.
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException, Body
import pandas as pd
import duckdb

from app.models.schemas import (
    MatchingRunRequest,
    MatchingStatusResponse,
    MatchingSummaryResponse,
    AssociationsPageResponse,
    UnmatchedPageResponse,
    MatchingEvaluationResponse,
    SensitivityParameterRow,
)
from app.services.matching_config import (
    MatchingConfig,
    CANDIDATE_SPATIAL_RADII_KM,
    CANDIDATE_TEMPORAL_WINDOWS_MINUTES,
)
from app.services.matching import (
    get_matching_status,
    get_matching_summary,
    get_matching_associations,
    get_matching_unmatched,
    get_matching_evaluation,
    execute_matching_workflow,
)
from app.config import settings

router = APIRouter(prefix="/matching", tags=["Spatial-Temporal Matching Engine"])


@router.get(
    "/status",
    response_model=MatchingStatusResponse,
    summary="Get Matching Engine Status",
)
async def get_status() -> MatchingStatusResponse:
    """Retrieve operational status and artifact readiness of the matching engine."""
    status_info = get_matching_status()
    return MatchingStatusResponse(**status_info)


@router.get(
    "/summary",
    response_model=MatchingSummaryResponse,
    summary="Get Matching Summary Results",
)
async def get_summary() -> MatchingSummaryResponse:
    """Retrieve top-level summary of candidate associations, multiplicity, and benchmarks."""
    summary_data = get_matching_summary()
    if not summary_data:
        raise HTTPException(
            status_code=404,
            detail="Matching summary not found. Please run the matching engine experiment first.",
        )
    return MatchingSummaryResponse(**summary_data)


@router.get(
    "/associations",
    response_model=AssociationsPageResponse,
    summary="Get Paginated Candidate Associations",
)
async def get_associations(
    limit: int = Query(50, ge=1, le=500, description="Number of associations to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    min_score: float = Query(0.0, ge=0.0, le=1.0, description="Minimum heuristic ranking score"),
    classification: Optional[str] = Query(None, description="Filter by classification: 'strong_proximity', 'candidate_association', 'ambiguous_association'"),
    multiplicity: Optional[str] = Query(None, description="Filter by multiplicity: '1:1', '1:N', 'N:1', 'M:N'"),
    sort_by: str = Query("heuristic_score", description="Sort field: 'heuristic_score', 'distance_km', 'time_diff_minutes'"),
    ascending: bool = Query(False, description="Sort direction ascending or descending"),
) -> AssociationsPageResponse:
    """Retrieve filtered, paginated candidate associations from Parquet storage."""
    result = get_matching_associations(
        limit=limit,
        offset=offset,
        min_score=min_score,
        classification=classification,
        multiplicity=multiplicity,
        sort_by=sort_by,
        ascending=ascending,
    )
    return AssociationsPageResponse(**result)


@router.get(
    "/unmatched",
    response_model=UnmatchedPageResponse,
    summary="Get Paginated Unmatched Observations",
)
async def get_unmatched(
    instrument: Optional[str] = Query(None, description="Filter by instrument: 'MODIS' or 'VIIRS'"),
    limit: int = Query(50, ge=1, le=500, description="Number of unmatched observations to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> UnmatchedPageResponse:
    """Retrieve filtered, paginated observations that found no candidate matches."""
    result = get_matching_unmatched(
        instrument=instrument,
        limit=limit,
        offset=offset,
    )
    return UnmatchedPageResponse(**result)


@router.get(
    "/evaluation",
    response_model=MatchingEvaluationResponse,
    summary="Get Sensitivity Evaluation Matrix",
)
async def get_evaluation() -> MatchingEvaluationResponse:
    """Retrieve sensitivity analysis across all 12 candidate parameter combinations."""
    rows = get_matching_evaluation()
    if not rows:
        raise HTTPException(
            status_code=404,
            detail="Sensitivity evaluation data not found. Please run the evaluation experiment first.",
        )

    matrix = [SensitivityParameterRow(**r) for r in rows]
    interpretation = (
        "Parameter sensitivity analysis reveals that increasing the spatial search radius from 1.25 km to 3.5 km "
        "substantially increases candidate association volume and multi-pixel cluster ambiguity (1:N and M:N), "
        "reflecting sensor footprint expansion and sub-pixel fire splitting. Similarly, expanding the temporal window "
        "from 15 minutes to 90 minutes increases cross-over associations (e.g. Terra morning to Aqua/NOAA-20 afternoon), "
        "capturing diurnal progression rather than simultaneous observations. Tight thresholds (1.25 km, 15 min) yield "
        "highest spatial-temporal coherence but report more unmatched observations. No single parameter set is universally "
        "optimal; thresholds must be selected based on analytical objectives (simultaneous verification vs. diurnal tracking)."
    )

    return MatchingEvaluationResponse(
        total_combinations=len(matrix),
        spatial_radii_km=CANDIDATE_SPATIAL_RADII_KM,
        temporal_windows_minutes=CANDIDATE_TEMPORAL_WINDOWS_MINUTES,
        matrix=matrix,
        scientific_interpretation=interpretation,
    )


@router.post(
    "/run",
    response_model=MatchingSummaryResponse,
    summary="Run Spatial-Temporal Matching on Subset",
)
async def run_matching(
    request: MatchingRunRequest = Body(...),
) -> MatchingSummaryResponse:
    """Execute spatial-temporal matching on a user-specified geographic region or slice."""
    cfg = MatchingConfig(
        spatial_radius_km=request.spatial_radius_km,
        temporal_window_minutes=request.temporal_window_minutes,
        weight_spatial=request.weight_spatial,
        weight_temporal=request.weight_temporal,
    )

    # Query subset from processed normalized files using DuckDB
    modis_path = settings.DATA_PROCESSED_DIR / "modis_normalized.csv"
    viirs_path = settings.DATA_PROCESSED_DIR / "viirs_normalized.csv"

    if not modis_path.exists() or not viirs_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Processed normalized datasets not found in data/processed/",
        )

    con = duckdb.connect()

    # Build spatial/temporal filter SQL
    where_parts = ["is_valid = true"]
    if request.min_lat is not None:
        where_parts.append(f"latitude >= {request.min_lat}")
    if request.max_lat is not None:
        where_parts.append(f"latitude <= {request.max_lat}")
    if request.min_lon is not None:
        where_parts.append(f"longitude >= {request.min_lon}")
    if request.max_lon is not None:
        where_parts.append(f"longitude <= {request.max_lon}")
    if request.start_date:
        where_parts.append(f"acquisition_date >= '{request.start_date}'")
    if request.end_date:
        where_parts.append(f"acquisition_date <= '{request.end_date}'")

    where_sql = " AND ".join(where_parts)
    limit_val = request.max_records or 50000

    try:
        modis_subset_df = con.execute(f"""
            SELECT * FROM '{modis_path.as_posix()}'
            WHERE {where_sql}
            LIMIT {limit_val}
        """).df()

        viirs_subset_df = con.execute(f"""
            SELECT * FROM '{viirs_path.as_posix()}'
            WHERE {where_sql}
            LIMIT {limit_val}
        """).df()
    finally:
        con.close()

    if modis_subset_df.empty or viirs_subset_df.empty:
        raise HTTPException(
            status_code=400,
            detail=f"Zero matching observations found for the specified filters (MODIS: {len(modis_subset_df)}, VIIRS: {len(viirs_subset_df)}).",
        )

    experiment_meta = {
        "region_filter": request.region or "custom",
        "bounds": {
            "min_lat": request.min_lat,
            "max_lat": request.max_lat,
            "min_lon": request.min_lon,
            "max_lon": request.max_lon,
        },
        "dates": {"start": request.start_date, "end": request.end_date},
        "records_sampled": {"modis": len(modis_subset_df), "viirs": len(viirs_subset_df)},
    }

    result = execute_matching_workflow(
        modis_subset_df,
        viirs_subset_df,
        config=cfg,
        run_grid_evaluation=True,
        experiment_metadata=experiment_meta,
        save_artifacts=True,
    )

    return MatchingSummaryResponse(**result["summary"])
