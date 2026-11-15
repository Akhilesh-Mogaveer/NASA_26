"""FastAPI Router for FireLens Phase 6 Temporal Event Evolution and Lifecycle Tracking.

Endpoints for same-sensor temporal cluster continuity, event track construction,
split/merge graph inspection, timeline visualization, and Leaflet map rendering.
"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Query, status

from app.services.evolution_manager import evolution_manager
from app.models.schemas import (
    EvolutionRunRequest,
    EvolutionJobStatusResponse,
    TemporalRelationshipsResponse,
    EventTracksResponse,
    EventTrackItem,
    TrackTimelineResponse,
    TrackLineageResponse,
    EvolutionMapResponse,
    EvolutionSummaryResponse,
    EvolutionExperimentItem,
)

router = APIRouter(
    prefix="/evolution",
    tags=["Temporal Event Evolution & Lifecycle Tracking"],
)


# =============================================================================
# Execution & Status Endpoints
# =============================================================================

@router.post(
    "/run",
    summary="Trigger Temporal Event Evolution Pipeline",
    response_model=Dict[str, Any],
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_evolution(payload: EvolutionRunRequest):
    """Start an asynchronous temporal cluster continuity and event track generation job."""
    result = evolution_manager.start_evolution_job({
        "max_temporal_gap_hours": payload.max_temporal_gap_hours,
        "max_spatial_distance_km": payload.max_spatial_distance_km,
        "use_extent_aware": payload.use_extent_aware,
        "max_centroid_cap_km": payload.max_centroid_cap_km,
        "candidate_selection_strategy": payload.candidate_selection_strategy,
        "ambiguity_delta_threshold": payload.ambiguity_delta_threshold,
        "experiment_name": payload.experiment_name,
    })
    if result.get("status") == "rejected":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=result.get("message", "An evolution job is already running"),
        )
    return result


@router.get(
    "/status",
    summary="Get Evolution Job Status",
    response_model=EvolutionJobStatusResponse,
)
async def get_evolution_status():
    """Retrieve progress and execution status of the current or last evolution job."""
    return EvolutionJobStatusResponse(**evolution_manager.evolution_job)


@router.get(
    "/summary",
    summary="Get Temporal Event Evolution Summary",
)
async def get_evolution_summary():
    """Retrieve overall summary metrics, track breakdowns, and split/merge statistics."""
    summary = evolution_manager.get_summary()
    if summary.get("status") == "uninitialized":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No evolution summary found. Run temporal evolution job first.",
        )
    return summary


# =============================================================================
# Event Track Endpoints
# =============================================================================

@router.get(
    "/tracks",
    summary="Query Paginated Event Tracks",
    response_model=EventTracksResponse,
)
async def get_tracks(
    sensor: Optional[str] = Query("ALL", description="Filter by sensor: ALL, MODIS, VIIRS"),
    track_type: Optional[str] = Query("ALL", description="Filter by track type: ALL, linear_track, branching_split, branching_merge, complex_network, isolated_cluster"),
    min_clusters: int = Query(1, ge=1, description="Minimum number of clusters in track"),
    min_duration_hours: float = Query(0.0, ge=0.0, description="Minimum observed duration in hours"),
    limit: int = Query(50, ge=1, le=500, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """Retrieve paginated temporal event tracks with topology, duration, and FRP metrics."""
    data = evolution_manager.get_tracks(
        sensor=sensor,
        track_type=track_type,
        min_clusters=min_clusters,
        min_duration_hours=min_duration_hours,
        limit=limit,
        offset=offset,
    )
    return EventTracksResponse(**data)


@router.get(
    "/tracks/{track_id}",
    summary="Get Single Event Track Detail",
    response_model=EventTrackItem,
)
async def get_track_detail(track_id: str):
    """Retrieve full summary metadata for a specific event track."""
    track = evolution_manager.get_track_detail(track_id)
    if not track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Track '{track_id}' not found.",
        )
    return EventTrackItem(**track)


@router.get(
    "/tracks/{track_id}/timeline",
    summary="Get Track Chronological Timeline",
    response_model=TrackTimelineResponse,
)
async def get_track_timeline(track_id: str):
    """Retrieve sequential observation timeline steps for an event track."""
    data = evolution_manager.get_track_timeline(track_id)
    if data["total_steps"] == 0:
        # Check if track exists
        track = evolution_manager.get_track_detail(track_id)
        if not track:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Track '{track_id}' not found.",
            )
    return TrackTimelineResponse(**data)


@router.get(
    "/tracks/{track_id}/lineage",
    summary="Get Track Lineage Graph",
    response_model=TrackLineageResponse,
)
async def get_track_lineage(track_id: str):
    """Retrieve directed lineage graph (nodes, edges, split/merge points) for an event track."""
    data = evolution_manager.get_track_lineage(track_id)
    if len(data["nodes"]) == 0:
        track = evolution_manager.get_track_detail(track_id)
        if not track:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Track '{track_id}' not found.",
            )
    return TrackLineageResponse(**data)


# =============================================================================
# Temporal Continuity Relationship Endpoints
# =============================================================================

@router.get(
    "/relationships",
    summary="Query Paginated Temporal Relationships",
    response_model=TemporalRelationshipsResponse,
)
async def get_relationships(
    sensor: Optional[str] = Query("ALL", description="Filter by sensor: ALL, MODIS, VIIRS"),
    classification: Optional[str] = Query("ALL", description="Classification: ALL, continuation_candidate, possible_split, possible_merge, complex_lineage"),
    min_score: float = Query(0.0, ge=0.0, le=1.0, description="Minimum heuristic score"),
    limit: int = Query(50, ge=1, le=500, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """Retrieve directed candidate temporal continuity edges between successive clusters."""
    data = evolution_manager.get_relationships(
        sensor=sensor,
        classification=classification,
        min_score=min_score,
        limit=limit,
        offset=offset,
    )
    return TemporalRelationshipsResponse(**data)


# =============================================================================
# Map & Experiments Endpoints
# =============================================================================

@router.get(
    "/map",
    summary="Get Map Nodes and Directed Edges",
    response_model=EvolutionMapResponse,
)
async def get_map_data(
    sensor: Optional[str] = Query("ALL", description="Filter by sensor: ALL, MODIS, VIIRS"),
    track_id: Optional[str] = Query(None, description="Optional filter to inspect a single track on the map"),
    lat_min: Optional[float] = Query(None, description="Minimum latitude viewport boundary"),
    lat_max: Optional[float] = Query(None, description="Maximum latitude viewport boundary"),
    lon_min: Optional[float] = Query(None, description="Minimum longitude viewport boundary"),
    lon_max: Optional[float] = Query(None, description="Maximum longitude viewport boundary"),
    limit: int = Query(300, ge=1, le=1000, description="Maximum items for map rendering"),
):
    """Retrieve cluster centroid nodes and directed continuity vector lines for Leaflet map display."""
    data = evolution_manager.get_map_data(
        sensor=sensor,
        track_id=track_id,
        lat_min=lat_min,
        lat_max=lat_max,
        lon_min=lon_min,
        lon_max=lon_max,
        limit=limit,
    )
    return EvolutionMapResponse(**data)


@router.get(
    "/experiments",
    summary="List Historical Evolution Experiments",
    response_model=List[EvolutionExperimentItem],
)
async def get_experiments():
    """Retrieve logs and benchmark metrics of historical evolution runs."""
    rows = evolution_manager.get_experiments()
    return [EvolutionExperimentItem(**r) for r in rows]
