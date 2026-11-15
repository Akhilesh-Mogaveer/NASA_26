"""Application configuration settings for FireLens backend."""
import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


# Project root path (2 levels up from backend/app)
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """FireLens backend configuration settings."""

    # API metadata
    API_TITLE: str = "FireLens API"
    API_DESCRIPTION: str = (
        "Harmonized Satellite Fire Intelligence Platform for MODIS and VIIRS active-fire observations."
    )
    API_VERSION: str = "0.1.0"
    API_PREFIX: str = "/api"

    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # CORS configuration - supports React dev servers
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # NASA FIRMS API (optional, for Phase 2+ direct downloads)
    FIRMS_MAP_KEY: str = ""

    # Data directory paths
    DATA_DIR: Path = BASE_DIR / "data"
    DATA_RAW_DIR: Path = BASE_DIR / "data" / "raw"
    DATA_RAW_MODIS: Path = BASE_DIR / "data" / "raw" / "modis"
    DATA_RAW_VIIRS: Path = BASE_DIR / "data" / "raw" / "viirs"
    DATA_PROCESSED_DIR: Path = BASE_DIR / "data" / "processed"
    DATA_REPORTS_DIR: Path = BASE_DIR / "data" / "reports"
    DATA_ANALYTICS_DIR: Path = BASE_DIR / "data" / "analytics"
    DATA_MATCHING_DIR: Path = BASE_DIR / "data" / "matching"
    DATA_EVENTS_DIR: Path = BASE_DIR / "data" / "events"
    DATA_EVOLUTION_DIR: Path = BASE_DIR / "data" / "evolution"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / "backend" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
