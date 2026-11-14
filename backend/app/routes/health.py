"""Health check route for FireLens API."""
from fastapi import APIRouter
from app.models.schemas import HealthResponse
from app.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, summary="API Health Check")
async def health_check() -> HealthResponse:
    """Verify backend API health and data directories availability."""
    data_dirs_status = {
        "data_dir": settings.DATA_DIR.exists(),
        "raw_modis": settings.DATA_RAW_MODIS.exists(),
        "raw_viirs": settings.DATA_RAW_VIIRS.exists(),
        "processed": settings.DATA_PROCESSED_DIR.exists(),
        "reports": settings.DATA_REPORTS_DIR.exists(),
    }
    return HealthResponse(
        status="healthy",
        service="FireLens API",
        version=settings.API_VERSION,
        data_directories=data_dirs_status,
    )
