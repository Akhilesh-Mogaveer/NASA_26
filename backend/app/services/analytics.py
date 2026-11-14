"""Analytics service for FireLens backend.

Provides high-performance, memory-safe access to precomputed multi-sensor
analytical artifacts derived from the 22.17M NASA FIRMS 2025 dataset.
"""
import csv
import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from app.config import settings

logger = logging.getLogger(__name__)

# In-memory caches to guarantee sub-millisecond API response latency
_CACHE: Dict[str, Any] = {}


def _get_analytics_dir() -> Path:
    """Get the analytics artifacts directory, ensuring it exists."""
    path = settings.DATA_ANALYTICS_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def _load_json_artifact(filename: str) -> Dict[str, Any]:
    """Load a JSON artifact with caching and error handling."""
    if filename in _CACHE:
        return _CACHE[filename]

    filepath = _get_analytics_dir() / filename
    if not filepath.exists():
        logger.warning(f"Analytics artifact {filename} does not exist at {filepath}")
        return {}

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            _CACHE[filename] = data
            return data
    except Exception as exc:
        logger.error(f"Error loading {filepath}: {exc}")
        return {}


def _load_csv_artifact(filename: str) -> List[Dict[str, Any]]:
    """Load a CSV artifact with caching and return as list of dicts."""
    cache_key = f"csv_{filename}"
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    filepath = _get_analytics_dir() / filename
    if not filepath.exists():
        logger.warning(f"CSV artifact {filename} does not exist at {filepath}")
        return []

    try:
        df = pd.read_csv(filepath)
        records = df.to_dict(orient="records")
        _CACHE[cache_key] = records
        return records
    except Exception as exc:
        logger.error(f"Error loading CSV {filepath}: {exc}")
        return []


def clear_analytics_cache():
    """Clear in-memory cache to force reloading from disk."""
    global _CACHE
    _CACHE.clear()


def get_analytics_overview() -> Dict[str, Any]:
    """Retrieve top-level platform overview metrics."""
    data = _load_json_artifact("analytics_summary.json")
    if not data:
        # Fallback default structure
        return {
            "generated_at": "",
            "dataset_provenance": "NASA FIRMS",
            "temporal_coverage": {"start_date": "", "end_date": "", "year": 2025},
            "counts": {"total_observations": 0, "valid_observations": 0, "invalid_observations": 0, "modis_count": 0, "viirs_count": 0, "viirs_to_modis_ratio": 0.0},
            "energetics": {"total_frp_mw": 0.0, "mean_frp_mw": 0.0, "modis_total_mw": 0.0, "viirs_total_mw": 0.0, "modis_mean_mw": 0.0, "viirs_mean_mw": 0.0},
            "geographical_extent": {"min_latitude": -90.0, "max_latitude": 90.0, "min_longitude": -180.0, "max_longitude": 180.0, "total_active_grid_cells": 0},
            "key_findings": [],
        }
    return data


def get_temporal_analytics() -> Dict[str, Any]:
    """Retrieve temporal distribution data (monthly, hourly, day-of-week, day/night)."""
    data = _load_json_artifact("temporal_summary.json")
    if not data:
        return {
            "generated_at": "",
            "monthly": [],
            "hourly": [],
            "day_of_week": [],
            "day_night": {"modis": {}, "viirs": {}},
        }
    return data


def get_frp_analytics() -> Dict[str, Any]:
    """Retrieve Fire Radiative Power parametric/non-parametric statistics and histogram."""
    data = _load_json_artifact("frp_statistics.json")
    if not data:
        return {
            "generated_at": "",
            "overall": {},
            "modis": {},
            "viirs": {},
            "histogram": [],
        }
    return data


def get_sensor_comparison_analytics() -> Dict[str, Any]:
    """Retrieve detailed scientific comparison between MODIS and VIIRS."""
    data = _load_json_artifact("sensor_comparison.json")
    if not data:
        return {
            "generated_at": "",
            "observations": {},
            "spatial_resolution": {},
            "frp_comparison": {},
            "confidence_distribution": {},
            "day_night_comparison": {},
            "orbital_parameters": {},
            "scientific_reasons_for_divergence": [],
        }
    return data


def get_geographical_analytics(top_n: int = 20) -> Dict[str, Any]:
    """Retrieve geographical distribution and top active 2-degree cells."""
    grid_cells = _load_csv_artifact("geographical_grid_density.csv")
    total_cells = len(grid_cells)
    top_cells = grid_cells[:top_n] if grid_cells else []

    # Calculate 5-degree latitudinal distribution from grid cells
    lat_bins: Dict[int, Dict[str, Any]] = {}
    for cell in grid_cells:
        lat = cell.get("lat_bin", 0.0)
        band = int(int(lat // 5.0) * 5)
        if band not in lat_bins:
            lat_bins[band] = {"lat_band": band, "modis_count": 0, "viirs_count": 0, "total_count": 0}
        lat_bins[band]["modis_count"] += int(cell.get("modis_count", 0))
        lat_bins[band]["viirs_count"] += int(cell.get("viirs_count", 0))
        lat_bins[band]["total_count"] += int(cell.get("total_count", 0))

    lat_dist = sorted(lat_bins.values(), key=lambda x: x["lat_band"])

    return {
        "total_active_cells": total_cells,
        "top_cells": top_cells,
        "latitudinal_distribution": lat_dist,
    }


def get_grid_density_data(
    min_count: int = 10,
    limit: int = 1500,
    offset: int = 0,
    sort_by: str = "total_count",
) -> List[Dict[str, Any]]:
    """Retrieve filtered and paginated 2-degree grid cell density for map rendering."""
    grid_cells = _load_csv_artifact("geographical_grid_density.csv")
    if not grid_cells:
        return []

    filtered = [cell for cell in grid_cells if cell.get("total_count", 0) >= min_count]
    return filtered[offset : offset + limit]
