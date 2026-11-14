"""NASA Data Ingestion, Validation, and Normalization Pipeline Coordinator.

Orchestrates loading from raw directories, validating records, normalizing schemas,
persisting processed datasets, and generating comprehensive data quality reports.
Supports streaming chunked execution for multi-gigabyte NASA FIRMS archives.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd

from app.config import settings
from app.services.ingestion import REQUIRED_COMMON_COLUMNS
from app.services.validation import validate_records, ValidationSummary
from app.services.normalization import normalize_dataset

logger = logging.getLogger(__name__)


class PipelineState:
    """Thread-safe status container for data processing pipeline."""
    def __init__(self):
        self.status: str = "idle"  # idle, processing, completed, error
        self.message: str = "Pipeline ready"
        self.last_run_at: Optional[str] = None
        self.last_summary: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "message": self.message,
            "last_run_at": self.last_run_at,
            "last_summary": self.last_summary,
        }


# Global pipeline state singleton
pipeline_state = PipelineState()


def run_ingestion_pipeline(
    raw_modis_dir: Optional[Path] = None,
    raw_viirs_dir: Optional[Path] = None,
    processed_dir: Optional[Path] = None,
    reports_dir: Optional[Path] = None,
    chunk_size: int = 250_000,
    max_rows_per_file: Optional[int] = None,
) -> Dict[str, Any]:
    """Execute the full Ingestion, Validation, and Normalization workflow in streaming chunks."""
    global pipeline_state

    modis_dir = raw_modis_dir or settings.DATA_RAW_MODIS
    viirs_dir = raw_viirs_dir or settings.DATA_RAW_VIIRS
    proc_dir = processed_dir or settings.DATA_PROCESSED_DIR
    rep_dir = reports_dir or settings.DATA_REPORTS_DIR

    # Ensure target output directories exist
    proc_dir.mkdir(parents=True, exist_ok=True)
    rep_dir.mkdir(parents=True, exist_ok=True)

    pipeline_state.status = "processing"
    pipeline_state.message = "Ingesting and validating NASA FIRMS observations"
    start_time = datetime.now(timezone.utc)

    report: Dict[str, Any] = {
        "report_generated_at": start_time.isoformat(),
        "number_of_source_files": 0,
        "source_files": [],
        "total_records": 0,
        "valid_records": 0,
        "invalid_records": 0,
        "invalid_coordinate_count": 0,
        "timestamp_errors": 0,
        "duplicate_counts": {
            "exact_duplicates": 0,
            "spatial_temporal_duplicates": 0,
            "total_flagged_duplicates": 0,
        },
        "missing_values_by_field": {},
        "processing_errors": [],
        "sensor_statistics": {
            "MODIS": {"total": 0, "valid": 0, "invalid": 0, "source_files": 0},
            "VIIRS": {"total": 0, "valid": 0, "invalid": 0, "source_files": 0},
        },
    }

    # Discover CSV files in both raw directories
    modis_files = sorted(modis_dir.glob("*.csv")) if modis_dir.exists() else []
    viirs_files = sorted(viirs_dir.glob("*.csv")) if viirs_dir.exists() else []
    
    # Filter out hidden or temporary files
    modis_files = [f for f in modis_files if not f.name.startswith(".")]
    viirs_files = [f for f in viirs_files if not f.name.startswith(".")]

    all_file_jobs = [(f, "MODIS") for f in modis_files] + [(f, "VIIRS") for f in viirs_files]
    report["number_of_source_files"] = len(all_file_jobs)
    report["sensor_statistics"]["MODIS"]["source_files"] = len(modis_files)
    report["sensor_statistics"]["VIIRS"]["source_files"] = len(viirs_files)

    # Initialize / clean output processed files
    modis_out_path = proc_dir / "modis_normalized.csv"
    viirs_out_path = proc_dir / "viirs_normalized.csv"
    unified_out_path = proc_dir / "unified_observations.csv"

    # Remove existing processed files to prevent duplicate appending
    for p in (modis_out_path, viirs_out_path, unified_out_path):
        if p.exists():
            try:
                p.unlink()
            except Exception as e:
                logger.warning("Could not unlink existing file %s: %s", p, e)

    modis_header_written = False
    viirs_header_written = False
    unified_header_written = False
    sensor_id_counters = {"MODIS": 0, "VIIRS": 0}

    try:
        for file_path, sensor in all_file_jobs:
            file_meta: Dict[str, Any] = {
                "filename": file_path.name,
                "sensor": sensor,
                "status": "loaded",
                "row_count": 0,
                "valid_records": 0,
                "invalid_records": 0,
                "error": None,
            }

            # 1. Inspect file existence and size
            if not file_path.exists():
                file_meta["status"] = "error"
                file_meta["error"] = "File does not exist"
                report["processing_errors"].append(file_meta)
                report["source_files"].append(file_meta)
                continue

            if file_path.stat().st_size == 0:
                file_meta["status"] = "error"
                file_meta["error"] = "File is empty (0 bytes)"
                report["processing_errors"].append(file_meta)
                report["source_files"].append(file_meta)
                continue

            # 2. Inspect CSV headers
            try:
                sample_head = pd.read_csv(file_path, nrows=0)
                original_cols = list(sample_head.columns)
            except Exception as exc:
                file_meta["status"] = "error"
                file_meta["error"] = f"Unreadable CSV headers: {str(exc)}"
                report["processing_errors"].append(file_meta)
                report["source_files"].append(file_meta)
                continue

            lower_cols = {c.lower().strip(): c for c in original_cols}
            missing_req = [req for req in REQUIRED_COMMON_COLUMNS if req not in lower_cols]
            if missing_req:
                file_meta["status"] = "error"
                file_meta["error"] = f"Missing required FIRMS columns: {', '.join(missing_req)}"
                report["processing_errors"].append(file_meta)
                report["source_files"].append(file_meta)
                continue

            # 3. Stream and process file in chunks
            file_rows_processed = 0
            file_valid = 0
            file_invalid = 0

            try:
                reader = pd.read_csv(
                    file_path,
                    chunksize=chunk_size,
                    dtype={"acq_time": str, "ACQ_TIME": str, "acq_date": str, "ACQ_DATE": str},
                    na_values=["", "NA", "N/A", "null", "NULL", "NaN"],
                    keep_default_na=True,
                    low_memory=False,
                )

                for chunk in reader:
                    if chunk.empty:
                        continue

                    # If max rows specified, slice chunk
                    if max_rows_per_file and (file_rows_processed + len(chunk) > max_rows_per_file):
                        limit_rows = max_rows_per_file - file_rows_processed
                        chunk = chunk.iloc[:limit_rows]

                    chunk["_source_file"] = file_path.name
                    chunk["_sensor_inferred"] = sensor

                    # Validate records
                    chunk_val, val_summary = validate_records(chunk, instrument=sensor)

                    # Normalize records
                    chunk_norm = normalize_dataset(
                        chunk_val,
                        instrument=sensor,
                        id_offset=sensor_id_counters[sensor],
                    )

                    # Append to sensor-specific output CSV
                    if sensor == "MODIS":
                        chunk_norm.to_csv(
                            modis_out_path,
                            mode="a",
                            header=not modis_header_written,
                            index=False,
                        )
                        modis_header_written = True
                    else:
                        chunk_norm.to_csv(
                            viirs_out_path,
                            mode="a",
                            header=not viirs_header_written,
                            index=False,
                        )
                        viirs_header_written = True

                    # Append to unified observations CSV
                    chunk_norm.to_csv(
                        unified_out_path,
                        mode="a",
                        header=not unified_header_written,
                        index=False,
                    )
                    unified_header_written = True

                    # Update counters
                    chunk_rows = len(chunk)
                    sensor_id_counters[sensor] += chunk_rows
                    file_rows_processed += chunk_rows
                    file_valid += val_summary.valid_records
                    file_invalid += val_summary.invalid_records

                    report["total_records"] += val_summary.total_records
                    report["valid_records"] += val_summary.valid_records
                    report["invalid_records"] += val_summary.invalid_records
                    report["invalid_coordinate_count"] += val_summary.invalid_coordinate_count
                    report["timestamp_errors"] += val_summary.timestamp_errors
                    report["duplicate_counts"]["exact_duplicates"] += val_summary.exact_duplicate_count
                    report["duplicate_counts"]["spatial_temporal_duplicates"] += val_summary.spatial_temporal_duplicate_count

                    for col, count in val_summary.missing_values_by_field.items():
                        report["missing_values_by_field"][col] = (
                            report["missing_values_by_field"].get(col, 0) + count
                        )

                    if max_rows_per_file and file_rows_processed >= max_rows_per_file:
                        break

            except Exception as exc:
                logger.error("Error processing CSV stream %s: %s", file_path.name, exc)
                file_meta["status"] = "error"
                file_meta["error"] = f"Stream processing error: {str(exc)}"
                report["processing_errors"].append(file_meta)

            if file_rows_processed == 0 and file_meta["status"] != "error":
                file_meta["status"] = "error"
                file_meta["error"] = "CSV contains 0 data rows"
                report["processing_errors"].append(file_meta)

            file_meta["row_count"] = file_rows_processed
            file_meta["valid_records"] = file_valid
            file_meta["invalid_records"] = file_invalid
            report["source_files"].append(file_meta)

            sensor_stats = report["sensor_statistics"][sensor]
            sensor_stats["total"] += file_rows_processed
            sensor_stats["valid"] += file_valid
            sensor_stats["invalid"] += file_invalid

        report["duplicate_counts"]["total_flagged_duplicates"] = (
            report["duplicate_counts"]["exact_duplicates"] +
            report["duplicate_counts"]["spatial_temporal_duplicates"]
        )

        # Ensure empty CSVs are created if no records existed
        if not modis_out_path.exists():
            pd.DataFrame().to_csv(modis_out_path, index=False)
        if not viirs_out_path.exists():
            pd.DataFrame().to_csv(viirs_out_path, index=False)
        if not unified_out_path.exists():
            pd.DataFrame().to_csv(unified_out_path, index=False)

        # Save Data Quality Report to disk
        quality_report_path = rep_dir / "data_quality_report.json"
        with open(quality_report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        pipeline_state.status = "completed"
        pipeline_state.message = (
            f"Successfully processed {report['total_records']:,} observations "
            f"({report['valid_records']:,} valid, {report['invalid_records']:,} invalid)"
        )
        pipeline_state.last_run_at = datetime.now(timezone.utc).isoformat()
        pipeline_state.last_summary = report

        return report

    except Exception as exc:
        logger.error("Pipeline failure: %s", exc, exc_info=True)
        pipeline_state.status = "error"
        pipeline_state.message = f"Pipeline failed: {str(exc)}"
        pipeline_state.last_run_at = datetime.now(timezone.utc).isoformat()
        report["processing_errors"].append({"error": str(exc)})
        return report


def get_latest_quality_report(reports_dir: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Load latest quality report from disk, or return None if not generated yet."""
    rep_dir = reports_dir or settings.DATA_REPORTS_DIR
    report_file = rep_dir / "data_quality_report.json"
    if report_file.exists():
        try:
            with open(report_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.error("Failed to read quality report: %s", exc)
            return None
    return None


def get_normalized_preview(
    sensor: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    processed_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Retrieve preview slice of normalized observations efficiently using chunked read."""
    proc_dir = processed_dir or settings.DATA_PROCESSED_DIR

    if sensor and sensor.upper() == "MODIS":
        file_to_read = proc_dir / "modis_normalized.csv"
    elif sensor and sensor.upper() == "VIIRS":
        file_to_read = proc_dir / "viirs_normalized.csv"
    else:
        file_to_read = proc_dir / "unified_observations.csv"

    if not file_to_read.exists() or file_to_read.stat().st_size == 0:
        return {
            "total_available": 0,
            "limit": limit,
            "offset": offset,
            "records": [],
            "source_dataset": file_to_read.name,
            "message": "No processed data available. Run POST /api/data/ingest first.",
        }

    try:
        # Read only up to offset + limit rows to avoid reading massive CSVs into memory
        rows_to_read = offset + limit + 100
        df = pd.read_csv(file_to_read, nrows=rows_to_read)
        if df.empty:
            return {
                "total_available": 0,
                "limit": limit,
                "offset": offset,
                "records": [],
                "source_dataset": file_to_read.name,
                "message": "Dataset is empty.",
            }

        if status:
            status_clean = status.lower().strip()
            if status_clean in ("valid", "invalid") and "processing_status" in df.columns:
                df = df[df["processing_status"] == status_clean]

        total_matching = len(df)
        slice_df = df.iloc[offset : offset + limit]
        records = slice_df.where(pd.notnull(slice_df), None).to_dict(orient="records")

        return {
            "total_available": total_matching,
            "limit": limit,
            "offset": offset,
            "records": records,
            "source_dataset": file_to_read.name,
            "message": "Success",
        }
    except Exception as exc:
        logger.error("Failed to read normalized preview: %s", exc)
        return {
            "total_available": 0,
            "limit": limit,
            "offset": offset,
            "records": [],
            "source_dataset": file_to_read.name,
            "message": f"Error loading preview: {str(exc)}",
        }
