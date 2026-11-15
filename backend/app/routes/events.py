"""FastAPI Router for FireLens Phase 5.1 & Phase 5.2 Event Intelligence.

Endpoints for independent fire event clustering, cross-sensor event association,
cluster/relationship queries, and interactive Leaflet map rendering.
"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Query, status

from app.services.events_manager import events_manager
from app.models.schemas import (
    ClusteringRunRequest,
    ClusteringJobStatusResponse,
    ClustersResponse,
    ClusterItem,
    ClusterObservationsResponse,
    EventAssociationRunRequest,
    EventAssociationJobStatusResponse,
    EventRelationshipsResponse,
    EventRelationshipItem,
    EventMapClustersResponse,
    EventMapLinesResponse,
)

router = APIRouter(
    prefix="/events",
    tags=["Fire Event Clustering & Association"],
)


# =============================================================================
# Phase 5.1: Independent Event Clustering Endpoints
# =============================================================================

@router.post(
    "/clustering/run",
    summary="Trigger Independent Event Clustering",
    response_model=Dict[str, Any],
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_clustering(payload: ClusteringRunRequest):
    """Start an asynchronous spatial-temporal clustering job for MODIS and VIIRS independently."""
    result = events_manager.start_clustering_job({
        "spatial_radius_km": payload.spatial_radius_km,
        "temporal_window_minutes": payload.temporal_window_minutes,
        "min_samples": payload.min_samples,
        "bounds": payload.bounds,
        "date_range": payload.date_range,
        "experiment_name": payload.experiment_name,
    })
    if result.get("status") == "rejected":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=result.get("message", "A clustering job is already active"),
        )
    return result


@router.get(
    "/clustering/status",
    summary="Get Clustering Job Status",
    response_model=ClusteringJobStatusResponse,
)
async def get_clustering_status():
    """Retrieve progress and execution status of the current or last clustering job."""
    return ClusteringJobStatusResponse(**events_manager.clustering_job)


@router.get(
    "/clustering/summary",
    summary="Get Clustering Summary and Benchmarks",
)
async def get_clustering_summary():
    """Retrieve the latest clustering summary metrics, parameters, and benchmarks."""
    summary = events_manager.get_clustering_summary()
    if summary.get("status") == "uninitialized":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No clustering summary found. Run clustering first.",
        )
    return summary


@router.get(
    "/clustering/clusters",
    summary="Query Paginated Fire Event Clusters",
    response_model=ClustersResponse,
)
async def get_clusters(
    sensor: Optional[str] = Query("ALL", description="Sensor filter: ALL, MODIS, or VIIRS"),
    min_obs: int = Query(1, ge=1, description="Minimum observations in cluster"),
    lat_min: Optional[float] = Query(None, description="Minimum latitude"),
    lat_max: Optional[float] = Query(None, description="Maximum latitude"),
    lon_min: Optional[float] = Query(None, description="Minimum longitude"),
    lon_max: Optional[float] = Query(None, description="Maximum longitude"),
    limit: int = Query(50, ge=1, le=500, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """Retrieve paginated clusters filtered by sensor and geographic bounding box."""
    data = events_manager.get_clusters(
        sensor=sensor,
        min_obs=min_obs,
        lat_min=lat_min,
        lat_max=lat_max,
        lon_min=lon_min,
        lon_max=lon_max,
        limit=limit,
        offset=offset,
    )
    return ClustersResponse(**data)


@router.get(
    "/clustering/{cluster_id}",
    summary="Get Specific Cluster Details",
    response_model=ClusterItem,
)
async def get_cluster_detail(cluster_id: str):
    """Retrieve comprehensive metadata, centroid, spatial extent, and FRP for a cluster."""
    cluster = events_manager.get_cluster_detail(cluster_id)
    if not cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cluster '{cluster_id}' not found.",
        )
    return ClusterItem(**cluster)


@router.get(
    "/clustering/{cluster_id}/observations",
    summary="Get Observations Belonging to a Cluster",
    response_model=ClusterObservationsResponse,
)
async def get_cluster_observations(
    cluster_id: str,
    limit: int = Query(100, ge=1, le=1000, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """Retrieve raw hotspot observations assigned to a specific cluster."""
    data = events_manager.get_cluster_observations(
        cluster_id=cluster_id,
        limit=limit,
        offset=offset,
    )
    if not data["observations"] and offset == 0:
        # Check if cluster itself exists
        if not events_manager.get_cluster_detail(cluster_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cluster '{cluster_id}' not found.",
            )
    return ClusterObservationsResponse(**data)


# =============================================================================
# Phase 5.2: Cross-Sensor Event Association Endpoints
# =============================================================================

@router.post(
    "/association/run",
    summary="Trigger Cross-Sensor Event Association",
    response_model=Dict[str, Any],
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_association(payload: EventAssociationRunRequest):
    """Start an asynchronous cross-sensor event association job using Phase 4 candidate edges."""
    result = events_manager.start_association_job({
        "min_supporting_pairs": payload.min_supporting_pairs,
        "ambiguity_delta_threshold": payload.ambiguity_delta_threshold,
    })
    if result.get("status") == "rejected":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=result.get("message", "An association job is already active"),
        )
    return result


@router.get(
    "/association/status",
    summary="Get Event Association Job Status",
    response_model=EventAssociationJobStatusResponse,
)
async def get_association_status():
    """Retrieve progress and execution status of the current or last event association job."""
    return EventAssociationJobStatusResponse(**events_manager.association_job)


@router.get(
    "/association/summary",
    summary="Get Cross-Sensor Event Association Summary",
)
async def get_association_summary():
    """Retrieve summary statistics, multiplicity breakdown, and topology counts."""
    summary = events_manager.get_association_summary()
    if summary.get("status") == "uninitialized":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No association summary found. Run event association first.",
        )
    return summary


@router.get(
    "/association/relationships",
    summary="Query Paginated Cross-Sensor Cluster Relationships",
    response_model=EventRelationshipsResponse,
)
async def get_relationships(
    multiplicity: Optional[str] = Query("ALL", description="Multiplicity filter: ALL, 1:1, 1:N, N:1, M:N"),
    classification: Optional[str] = Query("ALL", description="Classification: ALL, stronger_candidate, moderate_candidate, weak_candidate, ambiguous_candidate"),
    min_score: float = Query(0.0, ge=0.0, le=1.0, description="Minimum heuristic event score"),
    lat_min: Optional[float] = Query(None, description="Minimum latitude"),
    lat_max: Optional[float] = Query(None, description="Maximum latitude"),
    lon_min: Optional[float] = Query(None, description="Minimum longitude"),
    lon_max: Optional[float] = Query(None, description="Maximum longitude"),
    limit: int = Query(50, ge=1, le=500, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """Retrieve paginated candidate cluster relationships with supporting pair metrics."""
    data = events_manager.get_relationships(
        multiplicity=multiplicity,
        classification=classification,
        min_score=min_score,
        lat_min=lat_min,
        lat_max=lat_max,
        lon_min=lon_min,
        lon_max=lon_max,
        limit=limit,
        offset=offset,
    )
    return EventRelationshipsResponse(**data)


@router.get(
    "/association/{relationship_id}",
    summary="Get Specific Event Relationship Detail",
    response_model=EventRelationshipItem,
)
async def get_relationship_detail(relationship_id: str):
    """Retrieve full details of a specific MODIS-VIIRS cluster relationship."""
    rel = events_manager.get_relationship_detail(relationship_id)
    if not rel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relationship '{relationship_id}' not found.",
        )
    return EventRelationshipItem(**rel)


# =============================================================================
# Interactive Map Rendering Endpoints
# =============================================================================

@router.get(
    "/map/clusters",
    summary="Get Cluster Centroids for Map Rendering",
    response_model=EventMapClustersResponse,
)
async def get_map_clusters(
    lat_min: Optional[float] = Query(None, description="Minimum latitude"),
    lat_max: Optional[float] = Query(None, description="Maximum latitude"),
    lon_min: Optional[float] = Query(None, description="Minimum longitude"),
    lon_max: Optional[float] = Query(None, description="Maximum longitude"),
    sensor: Optional[str] = Query("ALL", description="Sensor filter: ALL, MODIS, or VIIRS"),
    limit: int = Query(300, ge=1, le=1000, description="Max clusters to return"),
):
    """Retrieve cluster centroid markers for map rendering."""
    items = events_manager.get_map_clusters(
        lat_min=lat_min,
        lat_max=lat_max,
        lon_min=lon_min,
        lon_max=lon_max,
        sensor=sensor,
        limit=limit,
    )
    return EventMapClustersResponse(clusters=items, count=len(items))


@router.get(
    "/map/relationships",
    summary="Get Relationship Vectors for Map Rendering",
    response_model=EventMapLinesResponse,
)
async def get_map_relationships(
    lat_min: Optional[float] = Query(None, description="Minimum latitude"),
    lat_max: Optional[float] = Query(None, description="Maximum latitude"),
    lon_min: Optional[float] = Query(None, description="Minimum longitude"),
    lon_max: Optional[float] = Query(None, description="Maximum longitude"),
    min_score: float = Query(0.0, ge=0.0, le=1.0, description="Minimum heuristic score"),
    limit: int = Query(300, ge=1, le=1000, description="Max vectors to return"),
):
    """Retrieve relationship lines connecting cluster centroids for map rendering."""
    items = events_manager.get_map_relationships(
        lat_min=lat_min,
        lat_max=lat_max,
        lon_min=lon_min,
        lon_max=lon_max,
        min_score=min_score,
        limit=limit,
    )
    return EventMapLinesResponse(lines=items, count=len(items))
