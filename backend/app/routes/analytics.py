"""Scientific Analytics API Routes for FireLens.

Exposes endpoints for high-level overview metrics, temporal dynamics,
Fire Radiative Power (FRP) distributions, geographical hotspot grids,
and multi-sensor MODIS vs. VIIRS comparisons.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query, HTTPException

from app.models.schemas import (
    AnalyticsOverviewResponse,
    TemporalAnalyticsResponse,
    FRPAnalyticsResponse,
    GeographicalAnalyticsResponse,
    SensorComparisonDetailedResponse,
    GridCellItem,
)
from app.services.analytics import (
    get_analytics_overview,
    get_temporal_analytics,
    get_frp_analytics,
    get_sensor_comparison_analytics,
    get_geographical_analytics,
    get_grid_density_data,
)

router = APIRouter(prefix="/analytics", tags=["Scientific Analytics"])


@router.get("/overview", response_model=AnalyticsOverviewResponse, summary="Get Platform Analytics Overview")
async def get_overview() -> AnalyticsOverviewResponse:
    """Retrieve top-level platform analytics across all 22.17M observations."""
    data = get_analytics_overview()
    if not data or not data.get("counts", {}).get("total_observations"):
        raise HTTPException(status_code=404, detail="Analytics data not found. Please ensure data processing has run.")
    return AnalyticsOverviewResponse(**data)


@router.get("/temporal", response_model=TemporalAnalyticsResponse, summary="Get Temporal Dynamics Analytics")
async def get_temporal() -> TemporalAnalyticsResponse:
    """Retrieve monthly, hourly (diurnal cycle), day-of-week, and day/night distributions."""
    data = get_temporal_analytics()
    if not data or not data.get("monthly"):
        raise HTTPException(status_code=404, detail="Temporal analytics data not found.")
    return TemporalAnalyticsResponse(**data)


@router.get("/frp", response_model=FRPAnalyticsResponse, summary="Get FRP Distribution Analytics")
async def get_frp() -> FRPAnalyticsResponse:
    """Retrieve Fire Radiative Power (MW) parametric metrics, percentiles, and histogram bins."""
    data = get_frp_analytics()
    if not data or not data.get("overall"):
        raise HTTPException(status_code=404, detail="FRP analytics data not found.")
    return FRPAnalyticsResponse(**data)


@router.get("/sensor-comparison", response_model=SensorComparisonDetailedResponse, summary="Get Sensor Comparison Analytics")
async def get_sensor_comparison() -> SensorComparisonDetailedResponse:
    """Retrieve detailed scientific comparison metrics between MODIS and VIIRS."""
    data = get_sensor_comparison_analytics()
    if not data or not data.get("observations"):
        raise HTTPException(status_code=404, detail="Sensor comparison analytics data not found.")
    return SensorComparisonDetailedResponse(**data)


@router.get("/geographical", response_model=GeographicalAnalyticsResponse, summary="Get Geographical Clustering Analytics")
async def get_geographical(
    top_n: int = Query(20, ge=1, le=100, description="Number of top 2-degree active cells to return")
) -> GeographicalAnalyticsResponse:
    """Retrieve geographical hotspot clusters and 5-degree latitudinal band distributions."""
    data = get_geographical_analytics(top_n=top_n)
    return GeographicalAnalyticsResponse(**data)


@router.get("/grid-density", response_model=List[GridCellItem], summary="Get 2-Degree Grid Cell Density")
async def get_grid_density(
    min_count: int = Query(10, ge=0, description="Minimum observations to include a cell"),
    limit: int = Query(1500, ge=1, le=5000, description="Maximum number of grid cells"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> List[GridCellItem]:
    """Retrieve filtered 2-degree grid cell density for interactive map layers."""
    cells = get_grid_density_data(min_count=min_count, limit=limit, offset=offset)
    return [GridCellItem(**c) for c in cells]
