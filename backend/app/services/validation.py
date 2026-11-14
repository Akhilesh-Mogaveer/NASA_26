"""NASA FIRMS Data Validation Service.

Validates coordinates, acquisition dates and times, numeric ranges,
missing values, and duplicate records without silently discarding invalid data.
Optimized for high-throughput vectorized execution across millions of records.
"""
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
    """Format raw FIRMS acquisition time (e.g. '345', '0345', '1420', '14:20') to HH:MM string."""
    if raw_time is None or pd.isna(raw_time):
        return None, None, None

    time_str = str(raw_time).strip()
    if not time_str or time_str.lower() in ("nan", "none", "null"):
        return None, None, None

    if "." in time_str:
        time_str = time_str.split(".")[0].strip()

    if ":" in time_str:
        parts = time_str.split(":")
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            hour = int(parts[0])
            minute = int(parts[1])
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return f"{hour:02d}:{minute:02d}", hour, minute
        return None, None, None

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
    """Combine date and time into UTC ISO-8601 string."""
    if date_str is None or pd.isna(date_str):
        return None, "Missing acquisition date"

    date_clean = str(date_str).strip()
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

    # 1. Track missing values across all source columns
    for col in df.columns:
        if not col.startswith("_"):
            missing_count = int(df[col].isna().sum())
            if missing_count > 0:
                summary.missing_values_by_field[col] = missing_count

    # 2. Duplicate Detection
    source_cols = [c for c in df.columns if not c.startswith("_")]
    exact_dup_mask = df.duplicated(subset=source_cols, keep="first")
    summary.exact_duplicate_count = int(exact_dup_mask.sum())

    if lat_col and lon_col and date_col and time_col:
        st_dup_mask = df.duplicated(subset=[lat_col, lon_col, date_col, time_col], keep="first")
        summary.spatial_temporal_duplicate_count = int(st_dup_mask.sum())
    else:
        st_dup_mask = pd.Series(False, index=df.index)

    # 3. Vectorized Coordinate Validation
    lat_series = pd.to_numeric(df[lat_col], errors="coerce") if lat_col else pd.Series(np.nan, index=df.index)
    lon_series = pd.to_numeric(df[lon_col], errors="coerce") if lon_col else pd.Series(np.nan, index=df.index)

    valid_lat = lat_series.notna() & (lat_series >= -90.0) & (lat_series <= 90.0)
    valid_lon = lon_series.notna() & (lon_series >= -180.0) & (lon_series <= 180.0)
    coord_valid = valid_lat & valid_lon
    invalid_coord_mask = ~coord_valid
    summary.invalid_coordinate_count = int(invalid_coord_mask.sum())

    # 4. Vectorized Time Validation & Formatting
    if time_col:
        raw_time_str = df[time_col].astype(str).str.split(".").str[0].str.strip()
        time_is_digit = raw_time_str.str.isdigit()
        time_len_ok = raw_time_str.str.len() <= 4
        padded_time = raw_time_str.str.zfill(4)
        
        hours = pd.to_numeric(padded_time.str[:2], errors="coerce")
        minutes = pd.to_numeric(padded_time.str[2:4], errors="coerce")
        
        valid_time_digits = time_is_digit & time_len_ok & (hours >= 0) & (hours <= 23) & (minutes >= 0) & (minutes <= 59)
        colon_mask = raw_time_str.str.contains(":")
        valid_time = valid_time_digits | colon_mask
        
        formatted_time = np.where(
            valid_time_digits,
            padded_time.str[:2] + ":" + padded_time.str[2:4],
            raw_time_str
        )
    else:
        valid_time = pd.Series(False, index=df.index)
        formatted_time = pd.Series("", index=df.index)

    if date_col:
        raw_date_str = df[date_col].astype(str).str.strip()
        valid_date = raw_date_str.str.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$") | raw_date_str.str.match(r"^\d{1,2}[-/]\d{1,2}[-/]\d{4}$")
    else:
        valid_date = pd.Series(False, index=df.index)

    timestamp_valid = valid_time & valid_date
    invalid_time_mask = ~timestamp_valid
    summary.timestamp_errors = int(invalid_time_mask.sum())

    iso_timestamps = np.where(
        timestamp_valid,
        raw_date_str + "T" + pd.Series(formatted_time, index=df.index) + ":00Z",
        None
    )

    # 5. Numeric Range Validation (FRP >= 0)
    if frp_col:
        frp_series = pd.to_numeric(df[frp_col], errors="coerce")
        valid_frp = df[frp_col].isna() | (frp_series.notna() & (frp_series >= 0.0))
    else:
        valid_frp = pd.Series(True, index=df.index)

    any_dup_mask = exact_dup_mask | st_dup_mask

    is_valid_mask = coord_valid & timestamp_valid & valid_frp & (~any_dup_mask)
    summary.valid_records = int(is_valid_mask.sum())
    summary.invalid_records = int((~is_valid_mask).sum())

    # 6. Detailed Error Construction for Invalid Rows
    error_list = [""] * len(df)
    invalid_indices = df.index[~is_valid_mask].tolist()

    for idx in invalid_indices:
        errors = []
        loc = df.index.get_loc(idx)
        if not valid_lat.iloc[loc]:
            val = df.iloc[loc][lat_col] if lat_col else "Missing"
            if pd.isna(val) or val == "Missing":
                errors.append("Latitude is missing")
            else:
                errors.append(f"Latitude out of bounds [-90, +90]: {val}")

        if not valid_lon.iloc[loc]:
            val = df.iloc[loc][lon_col] if lon_col else "Missing"
            if pd.isna(val) or val == "Missing":
                errors.append("Longitude is missing")
            else:
                errors.append(f"Longitude out of bounds [-180, +180]: {val}")

        if not valid_date.iloc[loc]:
            val = df.iloc[loc][date_col] if date_col else "Missing"
            errors.append(f"Invalid date format: '{val}'")

        if not valid_time.iloc[loc]:
            val = df.iloc[loc][time_col] if time_col else "Missing"
            errors.append(f"Invalid acquisition time: '{val}'")

        if not valid_frp.iloc[loc]:
            val = df.iloc[loc][frp_col] if frp_col else "Unknown"
            errors.append(f"FRP cannot be negative: {val}")

        if any_dup_mask.iloc[loc]:
            errors.append("Potential duplicate observation")

        err_str = "; ".join(errors)
        error_list[loc] = err_str

        if len(summary.validation_errors_sample) < 15:
            summary.validation_errors_sample.append({
                "row_index": int(idx),
                "source_file": str(df.iloc[loc].get("_source_file", "unknown")),
                "errors": errors,
            })

    df_validated = df.copy()
    df_validated["_is_valid"] = is_valid_mask
    df_validated["_validation_errors"] = error_list
    df_validated["_processing_status"] = np.where(is_valid_mask, "valid", "invalid")
    df_validated["_is_exact_duplicate"] = exact_dup_mask
    df_validated["_is_spatial_temporal_duplicate"] = st_dup_mask
    df_validated["_timestamp_utc"] = iso_timestamps
    df_validated["_formatted_acq_time"] = formatted_time

    return df_validated, summary
