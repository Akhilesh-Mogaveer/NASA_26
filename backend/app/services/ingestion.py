"""NASA FIRMS Data Ingestion Service.

Responsible for reading MODIS and VIIRS CSV files, inspecting headers,
preserving original raw fields, and recording source file provenance.
"""
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd

logger = logging.getLogger(__name__)

# Required core columns for active fire products
REQUIRED_COMMON_COLUMNS = ["latitude", "longitude", "acq_date", "acq_time"]


class IngestionError(Exception):
    """Raised when an ingestion error occurs on a dataset."""
    pass


class RawDataset:
    """Represents an ingested raw dataset with metadata."""
    def __init__(
        self,
        filepath: Path,
        sensor: str,
        df: pd.DataFrame,
        original_columns: List[str],
        row_count: int,
        status: str = "loaded",
        error_message: Optional[str] = None,
    ):
        self.filepath = filepath
        self.filename = filepath.name
        self.sensor = sensor.upper()
        self.df = df
        self.original_columns = original_columns
        self.row_count = row_count
        self.status = status
        self.error_message = error_message


def inspect_csv_headers(filepath: Path) -> List[str]:
    """Inspect CSV header line without reading entire file."""
    try:
        df_head = pd.read_csv(filepath, nrows=0)
        return list(df_head.columns)
    except Exception as exc:
        raise IngestionError(f"Failed to read headers from {filepath.name}: {exc}") from exc


def read_firms_csv(filepath: Path, expected_sensor: str) -> RawDataset:
    """Read a single NASA FIRMS CSV file and preserve original schema."""
    if not filepath.exists():
        return RawDataset(
            filepath=filepath,
            sensor=expected_sensor,
            df=pd.DataFrame(),
            original_columns=[],
            row_count=0,
            status="error",
            error_message="File does not exist",
        )

    # Check for empty file (0 bytes)
    if filepath.stat().st_size == 0:
        return RawDataset(
            filepath=filepath,
            sensor=expected_sensor,
            df=pd.DataFrame(),
            original_columns=[],
            row_count=0,
            status="error",
            error_message="File is empty (0 bytes)",
        )

    try:
        # Read CSV with string dtype for dates and times to prevent loss of leading zeros in acq_time (e.g. '0345')
        df = pd.read_csv(
            filepath,
            dtype={
                "acq_time": str,
                "ACQ_TIME": str,
                "acq_date": str,
                "ACQ_DATE": str,
            },
            na_values=["", "NA", "N/A", "null", "NULL", "NaN"],
            keep_default_na=True,
        )
    except Exception as exc:
        logger.error("Error reading CSV %s: %s", filepath, exc)
        return RawDataset(
            filepath=filepath,
            sensor=expected_sensor,
            df=pd.DataFrame(),
            original_columns=[],
            row_count=0,
            status="error",
            error_message=f"Unreadable CSV format: {str(exc)}",
        )

    original_cols = list(df.columns)
    row_count = len(df)

    if row_count == 0:
        return RawDataset(
            filepath=filepath,
            sensor=expected_sensor,
            df=df,
            original_columns=original_cols,
            row_count=0,
            status="error",
            error_message="CSV has header but contains 0 data rows",
        )

    # Check for required core columns (case-insensitive)
    lower_cols = {col.lower().strip(): col for col in original_cols}
    missing_required = [req for req in REQUIRED_COMMON_COLUMNS if req not in lower_cols]
    if missing_required:
        return RawDataset(
            filepath=filepath,
            sensor=expected_sensor,
            df=df,
            original_columns=original_cols,
            row_count=row_count,
            status="error",
            error_message=f"Missing required FIRMS columns: {', '.join(missing_required)}",
        )

    # Attach provenance attributes
    df["_source_file"] = filepath.name
    df["_sensor_inferred"] = expected_sensor.upper()

    return RawDataset(
        filepath=filepath,
        sensor=expected_sensor,
        df=df,
        original_columns=original_cols,
        row_count=row_count,
        status="loaded",
    )


def load_sensor_directory(dir_path: Path, sensor: str) -> List[RawDataset]:
    """Scan a sensor directory and load all CSV files."""
    datasets = []
    if not dir_path.exists():
        logger.warning("Directory does not exist: %s", dir_path)
        return datasets

    # Sort files for deterministic processing
    csv_files = sorted(dir_path.glob("*.csv"))
    for file in csv_files:
        # Ignore temporary or hidden files
        if file.name.startswith("."):
            continue
        dataset = read_firms_csv(file, expected_sensor=sensor)
        datasets.append(dataset)

    return datasets
