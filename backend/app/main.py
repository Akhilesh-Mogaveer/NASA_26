"""FireLens FastAPI Backend Main Application.

Harmonized Satellite Fire Intelligence Platform
NASA Space Apps Challenge 2026
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.config import settings
from app.models.schemas import RootResponse
from app.routes import health, data, analytics, matching, events, evolution


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Ensure all required data directories exist
    settings.DATA_RAW_MODIS.mkdir(parents=True, exist_ok=True)
    settings.DATA_RAW_VIIRS.mkdir(parents=True, exist_ok=True)
    settings.DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    settings.DATA_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    settings.DATA_ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
    settings.DATA_MATCHING_DIR.mkdir(parents=True, exist_ok=True)
    settings.DATA_EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    settings.DATA_EVOLUTION_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if not settings.DEBUG else ["*"],
    allow_credentials=True if not settings.DEBUG else False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler returning clean JSON responses."""
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred.",
            "error_type": type(exc).__name__,
            "message": str(exc),
        },
    )


@app.get(
    "/",
    response_model=RootResponse,
    summary="Root Endpoint",
    tags=["Root"],
)
async def root() -> RootResponse:
    """Check whether the FireLens API backend is running."""
    return RootResponse(
        message="FireLens API is running",
        status="success",
        version=settings.API_VERSION,
        docs_url="/docs",
    )


# Register API routers under /api
app.include_router(health.router, prefix=settings.API_PREFIX)
app.include_router(data.router, prefix=settings.API_PREFIX)
app.include_router(analytics.router, prefix=settings.API_PREFIX)
app.include_router(matching.router, prefix=settings.API_PREFIX)
app.include_router(events.router, prefix=settings.API_PREFIX)
app.include_router(evolution.router, prefix=settings.API_PREFIX)
# Also register /health for standard platform health probes (e.g., Render, Kubernetes)
app.include_router(health.router)
