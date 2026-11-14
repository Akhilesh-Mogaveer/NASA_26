"""NASA FIRMS Data Validation Service.

Validates coordinates, acquisition dates and times, numeric ranges,
missing values, and duplicate records without silently discarding invalid data.
"""
import re
import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np


class ValidationSummary:
    """Aggregated validation statistics for a batch or dataset."""
    def __init__(self):
        self.total_records = 0
        self.valid_records = 0
        self.invalid_records = 0
        self.invalid_coordinate_count = 0
        self.timestamp_errors = 0
        self.exact_duplicate_count = 0
        self.spatial_temporal_duplicate_count = 0
        self.missing_values_by_field: Dict[str, int] = {}
        self.validation_errors_sample: List[Dict[str, Any]] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_records": self.total_records,
            "valid_records": self.valid_records,
            "invalid_records": self.invalid_records,
            "invalid_coordinate_count": self.invalid_coordinate_count,
            "timestamp_errors": self.timestamp_errors,
            "exact_duplicate_count": self.exact_duplicate_count,
            "spatial_temporal_duplicate_count": self.spatial_temporal_duplicate_count,
            "missing_values_by_field": self.missing_values_by_field,
            "sample_errors": self.validation_errors_sample[:15],
        }


def format_acq_time(raw_time: Any) -> Tuple[Optional[str], Optional[int], Optional[int]]:
    """Format raw FIRMS acquisition time (e.g. '345', '0345', '1420', '14:20') to HH:MM string.
    
    Returns (formatted_time_str, hour, minute) or (None, None, None) on error.
    """
    if raw_time is None or pd.isna(raw_time):
        return None, None, None

    time_str = str(raw_time).strip()
    if not time_str or time_str.lower() in ("nan", "none", "null"):
        return None, None, None

    # Strip decimal points if read as float e.g. '345.0' -> '345'
    if "." in time_str:
        time_str = time_str.split(".")[0].strip()

    # If already formatted with colon (HH:MM)
    if ":" in time_str:
        parts = time_str.split(":")
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            hour = int(parts[0])
            minute = int(parts[1])
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return f"{hour:02d}:{minute:02d}", hour, minute
        return None, None, None

    # Handle 1-4 digit numeric strings (e.g. 5 -> 0005, 345 -> 0345, 1420 -> 1420)
    if time_str.isdigit():
        if len(time_str) > 4:
            return None, None, None
        padded = time_str.zfill(4)
        hour = int(padded[:2])
        minute = int(padded[2:])
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}", hour, minute

    return None, None, None


def parse_utc_timestamp(date_str: Any, time_str: Any) -> Tuple[Optional[str], Optional[str]]:
    """Combine date and time into UTC ISO-8601 string.
    
    Returns (iso_timestamp, error_message).
    """
    if date_str is None or pd.isna(date_str):
        return None, "Missing acquisition date"

    date_clean = str(date_str).strip()
    # Try standard YYYY-MM-DD
    parsed_date = None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%d-%m-%Y"):
        try:
            parsed_date = datetime.strptime(date_clean, fmt).date()
            break
        except ValueError:
            continue

    if parsed_date is None:
        return None, f"Invalid date format: '{date_clean}'"

    formatted_time, hour, minute = format_acq_time(time_str)
    if formatted_time is None:
        return None, f"Invalid acquisition time: '{time_str}'"

    dt_utc = datetime(
        year=parsed_date.year,
        month=parsed_date.month,
        day=parsed_date.day,
        hour=hour,
        minute=minute,
        tzinfo=timezone.utc,
    )
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ"), None


def validate_records(df: pd.DataFrame, instrument: str) -> Tuple[pd.DataFrame, ValidationSummary]:
    """Perform rigorous validation on dataset records without dropping invalid rows."""
    summary = ValidationSummary()
    summary.total_records = len(df)

    if df.empty:
        return df, summary

    # Case-insensitive column resolution
    col_map = {col.lower().strip(): col for col in df.columns}
    lat_col = col_map.get("latitude")
    lon_col = col_map.get("longitude")
    date_col = col_map.get("acq_date")
    time_col = col_map.get("acq_time")
    frp_col = col_map.get("frp")

    # Track missing values across all source columns
    for col in df.columns:
        if not col.startswith("_"):
            missing_count = int(df[col].isna().sum())
            if missing_count > 0:
                summary.missing_values_by_field[col] = missing_count

    # Check for exact duplicate rows (ignoring internal underscore columns)
    source_cols = [c for c in df.columns if not c.startswith("_")]
    exact_dup_mask = df.duplicated(subset=source_cols, keep="first")
    summary.exact_duplicate_count = int(exact_dup_mask.sum())

    # Check for spatial-temporal duplicate observations
    st_dup_mask = pd.Series(False, index=df.index)
    if lat_col and lon_col and date_col and time_col:
        st_dup_mask = df.duplicated(subset=[lat_col, lon_col, date_col, time_col], keep="first")
        summary.spatial_temporal_duplicate_count = int(st_dup_mask.sum())

    is_valid_list = []
    error_list = []
    timestamp_utc_list = []
    acq_time_clean_list = []

    for idx, row in df.iterrows():
        errors = []
        is_coord_error = False
        is_time_error = False

        # 1. Coordinate Validation
        raw_lat = row.get(lat_col) if lat_col else None
        raw_lon = row.get(lon_col) if lon_col else None

        if raw_lat is None or pd.isna(raw_lat):
            errors.append("Latitude is missing")
            is_coord_error = True
        else:
            try:
                lat_val = float(raw_lat)
                if math.isnan(lat_val) or lat_val < -90.0 or lat_val > 90.0:
                    errors.append(f"Latitude out of bounds [-90, +90]: {lat_val}")
                    is_coord_error = True
            except (ValueError, TypeError):
                errors.append(f"Latitude non-numeric: '{raw_lat}'")
                is_coord_error = True

        if raw_lon is None or pd.isna(raw_lon):
            errors.append("Longitude is missing")
            is_coord_error = True
        else:
            try:
                lon_val = float(raw_lon)
                if math.isnan(lon_val) or lon_val < -180.0 or lon_val > 180.0:
                    errors.append(f"Longitude out of bounds [-180, +180]: {lon_val}")
                    is_coord_error = True
            except (ValueError, TypeError):
                errors.append(f"Longitude non-numeric: '{raw_lon}'")
                is_coord_error = True

        if is_coord_error:
            summary.invalid_coordinate_count += 1

        # 2. Timestamp Validation
        raw_date = row.get(date_col) if date_col else None
        raw_time = row.get(time_col) if time_col else None
        formatted_time, _, _ = format_acq_time(raw_time)
        acq_time_clean_list.append(formatted_time or str(raw_time) if raw_time is not None else "")

        iso_ts, time_err = parse_utc_timestamp(raw_date, raw_time)
        if time_err:
            errors.append(time_err)
            is_time_error = True
            summary.timestamp_errors += 1
            timestamp_utc_list.append(None)
        else:
            timestamp_utc_list.append(iso_ts)

        # 3. Numeric checks (e.g. FRP, Scan, Track)
        if frp_col and row.get(frp_col) is not None and not pd.isna(row.get(frp_col)):
            try:
                frp_val = float(row.get(frp_col))
                if not math.isnan(frp_val) and frp_val < 0.0:
                    errors.append(f"FRP cannot be negative: {frp_val}")
            except (ValueError, TypeError):
                errors.append(f"FRP non-numeric: '{row.get(frp_col)}'")

        # 4. Duplicate annotation
        is_dup = bool(exact_dup_mask.loc[idx] or st_dup_mask.loc[idx])
        if is_dup:
            errors.append("Potential duplicate observation")

        # Compile record validity
        row_is_valid = len(errors) == 0
        if row_is_valid:
            summary.valid_records += 1
        else:
            summary.invalid_records += 1
            if len(summary.validation_errors_sample) < 15:
                summary.validation_errors_sample.append({
                    "row_index": int(idx),
                    "source_file": str(row.get("_source_file", "unknown")),
                    "errors": errors,
                })

        is_valid_list.append(row_is_valid)
        error_list.append("; ".join(errors) if errors else "")

    # Attach validation fields to DataFrame
    df_validated = df.copy()
    df_validated["_is_valid"] = is_valid_list
    df_validated["_validation_errors"] = error_list
    df_validated["_processing_status"] = np.where(df_validated["_is_valid"], "valid", "invalid")
    df_validated["_is_exact_duplicate"] = exact_dup_mask
    df_validated["_is_spatial_temporal_duplicate"] = st_dup_mask
    df_validated["_timestamp_utc"] = timestamp_utc_list
    df_validated["_formatted_acq_time"] = acq_time_clean_list

    return df_validated, summary
