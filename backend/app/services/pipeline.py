"""NASA Data Ingestion, Validation, and Normalization Pipeline Coordinator.

Orchestrates loading from raw directories, validating records, normalizing schemas,
persisting processed datasets, and generating comprehensive data quality reports.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd

from app.config import settings
from app.services.ingestion import load_sensor_directory, RawDataset
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
) -> Dict[str, Any]:
    """Execute the full Ingestion, Validation, and Normalization workflow."""
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

    try:
        # 1. Ingest Raw Datasets
        modis_raw_list = load_sensor_directory(modis_dir, sensor="MODIS")
        viirs_raw_list = load_sensor_directory(viirs_dir, sensor="VIIRS")
        all_raw_datasets = modis_raw_list + viirs_raw_list

        report["number_of_source_files"] = len(all_raw_datasets)
        report["sensor_statistics"]["MODIS"]["source_files"] = len(modis_raw_list)
        report["sensor_statistics"]["VIIRS"]["source_files"] = len(viirs_raw_list)

        modis_norm_dfs: List[pd.DataFrame] = []
        viirs_norm_dfs: List[pd.DataFrame] = []

        # 2. Process Each Dataset
        for raw_ds in all_raw_datasets:
            file_meta = {
                "filename": raw_ds.filename,
                "sensor": raw_ds.sensor,
                "status": raw_ds.status,
                "row_count": raw_ds.row_count,
                "error": raw_ds.error_message,
            }

            if raw_ds.status == "error":
                report["processing_errors"].append({
                    "filename": raw_ds.filename,
                    "sensor": raw_ds.sensor,
                    "error": raw_ds.error_message,
                })
                report["source_files"].append(file_meta)
                continue

            # Validate records
            df_val, val_summary = validate_records(raw_ds.df, instrument=raw_ds.sensor)

            # Normalize records
            df_norm = normalize_dataset(df_val, instrument=raw_ds.sensor)

            if raw_ds.sensor == "MODIS":
                modis_norm_dfs.append(df_norm)
            else:
                viirs_norm_dfs.append(df_norm)

            # Aggregate stats
            report["total_records"] += val_summary.total_records
            report["valid_records"] += val_summary.valid_records
            report["invalid_records"] += val_summary.invalid_records
            report["invalid_coordinate_count"] += val_summary.invalid_coordinate_count
            report["timestamp_errors"] += val_summary.timestamp_errors
            report["duplicate_counts"]["exact_duplicates"] += val_summary.exact_duplicate_count
            report["duplicate_counts"]["spatial_temporal_duplicates"] += val_summary.spatial_temporal_duplicate_count

            # Merge missing values
            for col, count in val_summary.missing_values_by_field.items():
                report["missing_values_by_field"][col] = (
                    report["missing_values_by_field"].get(col, 0) + count
                )

            # Sensor level breakdown
            sensor_stats = report["sensor_statistics"][raw_ds.sensor]
            sensor_stats["total"] += val_summary.total_records
            sensor_stats["valid"] += val_summary.valid_records
            sensor_stats["invalid"] += val_summary.invalid_records

            file_meta["valid_records"] = val_summary.valid_records
            file_meta["invalid_records"] = val_summary.invalid_records
            report["source_files"].append(file_meta)

        report["duplicate_counts"]["total_flagged_duplicates"] = (
            report["duplicate_counts"]["exact_duplicates"] +
            report["duplicate_counts"]["spatial_temporal_duplicates"]
        )

        # 3. Concatenate and Export Processed Datasets
        # MODIS
        if modis_norm_dfs:
            df_modis_all = pd.concat(modis_norm_dfs, ignore_index=True)
        else:
            df_modis_all = pd.DataFrame()
        modis_out_path = proc_dir / "modis_normalized.csv"
        df_modis_all.to_csv(modis_out_path, index=False)

        # VIIRS
        if viirs_norm_dfs:
            df_viirs_all = pd.concat(viirs_norm_dfs, ignore_index=True)
        else:
            df_viirs_all = pd.DataFrame()
        viirs_out_path = proc_dir / "viirs_normalized.csv"
        df_viirs_all.to_csv(viirs_out_path, index=False)

        # Unified
        unified_frames = [df for df in [df_modis_all, df_viirs_all] if not df.empty]
        if unified_frames:
            df_unified = pd.concat(unified_frames, ignore_index=True)
        else:
            df_unified = pd.DataFrame()
        unified_out_path = proc_dir / "unified_observations.csv"
        df_unified.to_csv(unified_out_path, index=False)

        # 4. Save Data Quality Report
        quality_report_path = rep_dir / "data_quality_report.json"
        with open(quality_report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        pipeline_state.status = "completed"
        pipeline_state.message = f"Successfully processed {report['total_records']} observations ({report['valid_records']} valid, {report['invalid_records']} invalid)"
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
    """Load latest quality report from disk, or return empty default if not generated yet."""
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
    """Retrieve preview slice of normalized observations from disk."""
    proc_dir = processed_dir or settings.DATA_PROCESSED_DIR

    # Choose dataset file based on sensor query
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
        df = pd.read_csv(file_to_read)
        if df.empty:
            return {
                "total_available": 0,
                "limit": limit,
                "offset": offset,
                "records": [],
                "source_dataset": file_to_read.name,
                "message": "Dataset is empty.",
            }

        # Apply status filter
        if status:
            status_clean = status.lower().strip()
            if status_clean in ("valid", "invalid") and "processing_status" in df.columns:
                df = df[df["processing_status"] == status_clean]

        total_matching = len(df)
        slice_df = df.iloc[offset : offset + limit]

        # Convert NaNs to None for JSON serialization
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
