"""NASA FIRMS Data Normalization Service.

Maps sensor-specific attributes from MODIS and VIIRS into a unified,
consistent observation schema while preserving all unedited source fields.
"""
import uuid
import hashlib
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
        if sat_upper in ("1", "J1", "NOAA-20", "JPSS-1", "NOAA20"):
            return "NOAA-20"
        if sat_upper in ("2", "J2", "NOAA-21", "JPSS-2", "NOAA21"):
            return "NOAA-21"
        return sat_str

    return sat_str


def generate_observation_id(sensor: str, filename: str, row_idx: int, lat: Any, lon: Any, date: Any, time: Any) -> str:
    """Generate a stable, deterministic, unique observation identifier."""
    hash_input = f"{filename}_{row_idx}_{lat}_{lon}_{date}_{time}".encode("utf-8")
    hash_hex = hashlib.sha1(hash_input).hexdigest()[:8].upper()
    return f"FL-{sensor.upper()[:3]}-{hash_hex}-{row_idx:06d}"


def normalize_dataset(df_validated: pd.DataFrame, instrument: str) -> pd.DataFrame:
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

    # Sensor-specific brightness temperature
    # MODIS: 'brightness' (T21/T22) and 'bright_t31'
    # VIIRS: 'bright_ti4' (I4 band) and 'bright_ti5'
    brightness_col = col_map.get("brightness") or col_map.get("bright_ti4")

    records = []
    for idx, row in df_validated.iterrows():
        source_file = str(row.get("_source_file", "unknown"))

        # Safe coordinate extraction
        try:
            lat = float(row[lat_col]) if lat_col and pd.notna(row[lat_col]) else None
        except (ValueError, TypeError):
            lat = None

        try:
            lon = float(row[lon_col]) if lon_col and pd.notna(row[lon_col]) else None
        except (ValueError, TypeError):
            lon = None

        acq_date = str(row[date_col]).strip() if date_col and pd.notna(row[date_col]) else None
        acq_time = row.get("_formatted_acq_time") or (str(row[time_col]).strip() if time_col and pd.notna(row[time_col]) else None)
        timestamp_utc = row.get("_timestamp_utc")

        # Canonical satellite
        raw_sat = row.get(sat_col) if sat_col else None
        satellite = normalize_satellite_name(raw_sat, instrument_clean)

        # FRP
        frp_val = None
        if frp_col and pd.notna(row[frp_col]):
            try:
                frp_val = round(float(row[frp_col]), 2)
            except (ValueError, TypeError):
                frp_val = None

        # Confidence: preserve exact type (integer for MODIS, string for VIIRS)
        confidence_val = None
        if conf_col and pd.notna(row[conf_col]):
            raw_conf = row[conf_col]
            if instrument_clean == "MODIS":
                try:
                    confidence_val = int(float(raw_conf))
                except (ValueError, TypeError):
                    confidence_val = str(raw_conf)
            else:
                confidence_val = str(raw_conf).strip().lower()

        # Brightness
        brightness_val = None
        if brightness_col and pd.notna(row[brightness_col]):
            try:
                brightness_val = round(float(row[brightness_col]), 2)
            except (ValueError, TypeError):
                brightness_val = None

        # Scan & Track
        scan_val = None
        if scan_col and pd.notna(row[scan_col]):
            try:
                scan_val = round(float(row[scan_col]), 2)
            except (ValueError, TypeError):
                scan_val = None

        track_val = None
        if track_col and pd.notna(row[track_col]):
            try:
                track_val = round(float(row[track_col]), 2)
            except (ValueError, TypeError):
                track_val = None

        # Day/Night
        daynight_val = None
        if daynight_col and pd.notna(row[daynight_col]):
            daynight_val = str(row[daynight_col]).strip().upper()

        obs_id = generate_observation_id(instrument_clean, source_file, int(idx), lat, lon, acq_date, acq_time)

        # Normalized common record
        norm_record = {
            "observation_id": obs_id,
            "latitude": lat,
            "longitude": lon,
            "acquisition_date": acq_date,
            "acquisition_time": acq_time,
            "timestamp_utc": timestamp_utc,
            "satellite": satellite,
            "instrument": instrument_clean,
            "confidence": confidence_val,
            "frp": frp_val,
            "brightness": brightness_val,
            "scan": scan_val,
            "track": track_val,
            "daynight": daynight_val,
            "source_file": source_file,
            "processing_status": row.get("_processing_status", "valid"),
            "is_valid": bool(row.get("_is_valid", True)),
            "validation_errors": row.get("_validation_errors", ""),
            "is_duplicate": bool(row.get("_is_exact_duplicate", False) or row.get("_is_spatial_temporal_duplicate", False)),
        }

        # Preserve all original raw columns with 'raw_' prefix to guarantee 100% data preservation
        for orig_c in df_validated.columns:
            if not orig_c.startswith("_"):
                norm_record[f"raw_{orig_c}"] = row[orig_c]

        records.append(norm_record)

    return pd.DataFrame(records)
