"""NASA FIRMS Data Normalization Service.

Maps sensor-specific attributes from MODIS and VIIRS into a unified,
consistent observation schema while preserving all unedited source fields.
Optimized for high-throughput vectorized execution across millions of records.
"""
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np


def normalize_satellite_name(raw_sat: Any, instrument: str) -> Optional[str]:
    """Map raw FIRMS satellite codes to standard canonical satellite platform names."""
    if raw_sat is None or pd.isna(raw_sat):
        return None

    sat_str = str(raw_sat).strip()
    sat_upper = sat_str.upper()

    if instrument.upper() == "MODIS":
        if sat_upper in ("T", "TERRA"):
            return "Terra"
        if sat_upper in ("A", "AQUA"):
            return "Aqua"
        return sat_str

    if instrument.upper() == "VIIRS":
        if sat_upper in ("N", "NPP", "SNPP", "SUOMI-NPP", "SUOMI NPP"):
            return "Suomi-NPP"
        if sat_upper in ("1", "J1", "NOAA-20", "JPSS-1", "NOAA20", "N20"):
            return "NOAA-20"
        if sat_upper in ("2", "J2", "NOAA-21", "JPSS-2", "NOAA21", "N21"):
            return "NOAA-21"
        return sat_str

    return sat_str


def normalize_dataset(df_validated: pd.DataFrame, instrument: str, id_offset: int = 0) -> pd.DataFrame:
    """Transform validated DataFrame into common normalized representation while preserving raw columns."""
    if df_validated.empty:
        return pd.DataFrame()

    instrument_clean = instrument.upper()
    col_map = {col.lower().strip(): col for col in df_validated.columns}

    # Core field lookups
    lat_col = col_map.get("latitude")
    lon_col = col_map.get("longitude")
    date_col = col_map.get("acq_date")
    time_col = col_map.get("acq_time")
    sat_col = col_map.get("satellite")
    frp_col = col_map.get("frp")
    conf_col = col_map.get("confidence")
    scan_col = col_map.get("scan")
    track_col = col_map.get("track")
    daynight_col = col_map.get("daynight")
    brightness_col = col_map.get("brightness") or col_map.get("bright_ti4")

    num_rows = len(df_validated)
    df_norm = pd.DataFrame(index=df_validated.index)

    # 1. Observation ID (Deterministic, unique, sequential)
    sensor_prefix = "MOD" if instrument_clean == "MODIS" else "VII"
    df_norm["observation_id"] = [
        f"FL-{sensor_prefix}-{id_offset + i:08d}" for i in range(num_rows)
    ]

    # 2. Coordinates
    df_norm["latitude"] = pd.to_numeric(df_validated[lat_col], errors="coerce") if lat_col else None
    df_norm["longitude"] = pd.to_numeric(df_validated[lon_col], errors="coerce") if lon_col else None

    # 3. Timestamps
    df_norm["acquisition_date"] = df_validated[date_col].astype(str).str.strip() if date_col else None
    df_norm["acquisition_time"] = df_validated["_formatted_acq_time"] if "_formatted_acq_time" in df_validated.columns else (
        df_validated[time_col].astype(str) if time_col else None
    )
    df_norm["timestamp_utc"] = df_validated["_timestamp_utc"] if "_timestamp_utc" in df_validated.columns else None

    # 4. Satellite & Instrument
    if sat_col:
        df_norm["satellite"] = df_validated[sat_col].apply(lambda s: normalize_satellite_name(s, instrument_clean))
    else:
        df_norm["satellite"] = None
    df_norm["instrument"] = instrument_clean

    # 5. Sensor Confidence (Keep exact conventions)
    if conf_col:
        if instrument_clean == "MODIS":
            df_norm["confidence"] = pd.to_numeric(df_validated[conf_col], errors="coerce")
        else:
            df_norm["confidence"] = df_validated[conf_col].astype(str).str.strip().str.lower()
    else:
        df_norm["confidence"] = None

    # 6. Radiometry & Sensor Geometry
    df_norm["frp"] = pd.to_numeric(df_validated[frp_col], errors="coerce").round(2) if frp_col else None
    df_norm["brightness"] = pd.to_numeric(df_validated[brightness_col], errors="coerce").round(2) if brightness_col else None
    df_norm["scan"] = pd.to_numeric(df_validated[scan_col], errors="coerce").round(2) if scan_col else None
    df_norm["track"] = pd.to_numeric(df_validated[track_col], errors="coerce").round(2) if track_col else None
    df_norm["daynight"] = df_validated[daynight_col].astype(str).str.strip().str.upper() if daynight_col else None

    # 7. Metadata & Validation Flags
    df_norm["source_file"] = df_validated["_source_file"] if "_source_file" in df_validated.columns else "unknown"
    df_norm["processing_status"] = df_validated["_processing_status"] if "_processing_status" in df_validated.columns else "valid"
    df_norm["is_valid"] = df_validated["_is_valid"] if "_is_valid" in df_validated.columns else True
    df_norm["validation_errors"] = df_validated["_validation_errors"] if "_validation_errors" in df_validated.columns else ""
    df_norm["is_duplicate"] = (
        df_validated["_is_exact_duplicate"] | df_validated["_is_spatial_temporal_duplicate"]
        if "_is_exact_duplicate" in df_validated.columns else False
    )

    # 8. Preserve all original raw columns with 'raw_' prefix
    for orig_c in df_validated.columns:
        if not orig_c.startswith("_"):
            df_norm[f"raw_{orig_c}"] = df_validated[orig_c]

    return df_norm
