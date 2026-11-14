"""Test Suite for NASA FIRMS Data Ingestion, Validation, and Normalization.

NOTE: All test datasets are purely SYNTHETIC fixtures designed specifically for
automated unit testing and are explicitly labeled as such.
"""
import json
import pytest
from pathlib import Path
import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from app.services.ingestion import read_firms_csv, load_sensor_directory
from app.services.validation import validate_records
from app.services.normalization import normalize_dataset
from app.services.pipeline import run_ingestion_pipeline, get_normalized_preview

client = TestClient(app)

# Synthetic test data fixtures
SYNTHETIC_MODIS_VALID_CSV = """latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_t31,frp,daynight
12.9100,74.8500,318.5,1.1,1.0,2026-11-14,0345,Terra,MODIS,85,6.1NRT,296.2,15.4,D
13.0500,75.1200,305.1,1.2,1.1,2026-11-14,1420,Aqua,MODIS,70,6.1NRT,290.0,8.2,N
"""

SYNTHETIC_VIIRS_VALID_CSV = """latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight
12.9120,74.8510,326.8,0.4,0.4,2026-11-14,0340,N,VIIRS,nominal,2.0NRT,297.5,11.2,D
13.0510,75.1210,335.0,0.38,0.38,2026-11-14,0830,1,VIIRS,high,2.0NRT,301.2,18.6,D
"""


@pytest.fixture
def test_dirs(tmp_path: Path):
    """Create isolated temporary directories for synthetic test datasets."""
    raw_modis = tmp_path / "raw" / "modis"
    raw_viirs = tmp_path / "raw" / "viirs"
    processed = tmp_path / "processed"
    reports = tmp_path / "reports"

    raw_modis.mkdir(parents=True, exist_ok=True)
    raw_viirs.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)

    return {
        "raw_modis": raw_modis,
        "raw_viirs": raw_viirs,
        "processed": processed,
        "reports": reports,
    }


def test_valid_modis_ingestion_and_validation(test_dirs):
    """Verify ingestion, validation, and normalization of valid synthetic MODIS CSV."""
    csv_file = test_dirs["raw_modis"] / "synthetic_modis.csv"
    csv_file.write_text(SYNTHETIC_MODIS_VALID_CSV, encoding="utf-8")

    raw_ds = read_firms_csv(csv_file, expected_sensor="MODIS")
    assert raw_ds.status == "loaded"
    assert raw_ds.row_count == 2

    df_val, summary = validate_records(raw_ds.df, instrument="MODIS")
    assert summary.valid_records == 2
    assert summary.invalid_records == 0
    assert summary.invalid_coordinate_count == 0
    assert summary.timestamp_errors == 0

    df_norm = normalize_dataset(df_val, instrument="MODIS")
    assert len(df_norm) == 2
    assert "observation_id" in df_norm.columns
    assert "timestamp_utc" in df_norm.columns
    assert df_norm.iloc[0]["instrument"] == "MODIS"
    assert df_norm.iloc[0]["satellite"] == "Terra"
    assert df_norm.iloc[0]["confidence"] == 85
    assert df_norm.iloc[0]["timestamp_utc"] == "2026-11-14T03:45:00Z"
    # Ensure source columns are preserved with raw_ prefix
    assert "raw_brightness" in df_norm.columns


def test_valid_viirs_ingestion_and_validation(test_dirs):
    """Verify ingestion, validation, and normalization of valid synthetic VIIRS CSV."""
    csv_file = test_dirs["raw_viirs"] / "synthetic_viirs.csv"
    csv_file.write_text(SYNTHETIC_VIIRS_VALID_CSV, encoding="utf-8")

    raw_ds = read_firms_csv(csv_file, expected_sensor="VIIRS")
    assert raw_ds.status == "loaded"
    assert raw_ds.row_count == 2

    df_val, summary = validate_records(raw_ds.df, instrument="VIIRS")
    assert summary.valid_records == 2
    assert summary.invalid_records == 0

    df_norm = normalize_dataset(df_val, instrument="VIIRS")
    assert len(df_norm) == 2
    # Verify satellite mapping (N -> Suomi-NPP, 1 -> NOAA-20)
    assert df_norm.iloc[0]["satellite"] == "Suomi-NPP"
    assert df_norm.iloc[1]["satellite"] == "NOAA-20"
    # Verify categorical confidence preserved
    assert df_norm.iloc[0]["confidence"] == "nominal"
    assert df_norm.iloc[1]["confidence"] == "high"


def test_missing_required_columns(test_dirs):
    """Verify error reporting when critical columns (latitude, longitude, etc.) are absent."""
    broken_csv = test_dirs["raw_modis"] / "synthetic_missing_cols.csv"
    broken_csv.write_text("latitude,brightness,scan\n12.5,310.0,1.0\n", encoding="utf-8")

    raw_ds = read_firms_csv(broken_csv, expected_sensor="MODIS")
    assert raw_ds.status == "error"
    assert "Missing required FIRMS columns" in raw_ds.error_message


def test_invalid_coordinates(test_dirs):
    """Verify detection of latitude and longitude outside valid bounds."""
    invalid_coord_csv = test_dirs["raw_modis"] / "synthetic_bad_coords.csv"
    content = """latitude,longitude,acq_date,acq_time,instrument
95.5000,74.8500,2026-11-14,0345,MODIS
12.5000,195.0000,2026-11-14,0345,MODIS
-92.0000,-185.0000,2026-11-14,0345,MODIS
"""
    invalid_coord_csv.write_text(content, encoding="utf-8")

    raw_ds = read_firms_csv(invalid_coord_csv, expected_sensor="MODIS")
    df_val, summary = validate_records(raw_ds.df, instrument="MODIS")

    assert summary.total_records == 3
    assert summary.invalid_records == 3
    assert summary.invalid_coordinate_count == 3
    assert all(df_val["_processing_status"] == "invalid")


def test_invalid_timestamps(test_dirs):
    """Verify detection of invalid date or hour/minute timestamps."""
    bad_time_csv = test_dirs["raw_modis"] / "synthetic_bad_times.csv"
    content = """latitude,longitude,acq_date,acq_time,instrument
12.5000,74.8500,2026-11-14,2599,MODIS
12.5000,74.8500,not-a-date,0345,MODIS
"""
    bad_time_csv.write_text(content, encoding="utf-8")

    raw_ds = read_firms_csv(bad_time_csv, expected_sensor="MODIS")
    df_val, summary = validate_records(raw_ds.df, instrument="MODIS")

    assert summary.timestamp_errors >= 2
    assert summary.invalid_records == 2


def test_missing_values_not_replaced_with_zero(test_dirs):
    """Verify missing values are identified and preserved without replacing nulls with zero."""
    null_val_csv = test_dirs["raw_modis"] / "synthetic_nulls.csv"
    content = """latitude,longitude,acq_date,acq_time,instrument,frp,confidence
12.5000,74.8500,2026-11-14,0345,MODIS,,
"""
    null_val_csv.write_text(content, encoding="utf-8")

    raw_ds = read_firms_csv(null_val_csv, expected_sensor="MODIS")
    df_val, summary = validate_records(raw_ds.df, instrument="MODIS")
    df_norm = normalize_dataset(df_val, instrument="MODIS")

    assert summary.missing_values_by_field.get("frp", 0) == 1
    # Check that FRP is None/NaN, NOT zero
    assert df_norm.iloc[0]["frp"] is None or pd.isna(df_norm.iloc[0]["frp"])


def test_duplicate_records_detection(test_dirs):
    """Verify that exact and spatial-temporal duplicate observations are flagged without deletion."""
    dup_csv = test_dirs["raw_modis"] / "synthetic_dups.csv"
    content = """latitude,longitude,acq_date,acq_time,instrument,frp
12.5000,74.8500,2026-11-14,0345,MODIS,10.5
12.5000,74.8500,2026-11-14,0345,MODIS,10.5
12.5000,74.8500,2026-11-14,0345,MODIS,22.0
"""
    dup_csv.write_text(content, encoding="utf-8")

    raw_ds = read_firms_csv(dup_csv, expected_sensor="MODIS")
    df_val, summary = validate_records(raw_ds.df, instrument="MODIS")

    assert summary.exact_duplicate_count == 1
    assert summary.spatial_temporal_duplicate_count == 2
    # Verify records were NOT silently dropped
    assert len(df_val) == 3


def test_empty_csv_file_handling(test_dirs):
    """Verify that an empty file (0 bytes) is handled gracefully without crashing."""
    empty_file = test_dirs["raw_modis"] / "synthetic_empty.csv"
    empty_file.write_text("", encoding="utf-8")

    raw_ds = read_firms_csv(empty_file, expected_sensor="MODIS")
    assert raw_ds.status == "error"
    assert "empty" in raw_ds.error_message.lower()


def test_unreadable_csv_handling(test_dirs):
    """Verify that corrupted or unreadable CSV is handled gracefully."""
    bad_file = test_dirs["raw_modis"] / "synthetic_corrupt.csv"
    bad_file.write_bytes(b"\x00\xff\xfe\x00corrupted\x00data\x00")

    raw_ds = read_firms_csv(bad_file, expected_sensor="MODIS")
    # Should catch gracefully and flag status as error
    assert raw_ds.status == "error"


def test_full_pipeline_output_generation(test_dirs):
    """Verify execution of full pipeline and persistence of processed CSVs and quality report."""
    modis_file = test_dirs["raw_modis"] / "synthetic_modis.csv"
    modis_file.write_text(SYNTHETIC_MODIS_VALID_CSV, encoding="utf-8")

    viirs_file = test_dirs["raw_viirs"] / "synthetic_viirs.csv"
    viirs_file.write_text(SYNTHETIC_VIIRS_VALID_CSV, encoding="utf-8")

    report = run_ingestion_pipeline(
        raw_modis_dir=test_dirs["raw_modis"],
        raw_viirs_dir=test_dirs["raw_viirs"],
        processed_dir=test_dirs["processed"],
        reports_dir=test_dirs["reports"],
    )

    assert report["total_records"] == 4
    assert report["valid_records"] == 4
    assert report["invalid_records"] == 0

    # Verify generated files exist
    modis_out = test_dirs["processed"] / "modis_normalized.csv"
    viirs_out = test_dirs["processed"] / "viirs_normalized.csv"
    unified_out = test_dirs["processed"] / "unified_observations.csv"
    report_out = test_dirs["reports"] / "data_quality_report.json"

    assert modis_out.exists()
    assert viirs_out.exists()
    assert unified_out.exists()
    assert report_out.exists()

    df_unified = pd.read_csv(unified_out)
    assert len(df_unified) == 4
    assert set(df_unified["instrument"].unique()) == {"MODIS", "VIIRS"}

    with open(report_out, "r", encoding="utf-8") as f:
        saved_report = json.load(f)
    assert saved_report["total_records"] == 4


def test_api_data_endpoints():
    """Verify the FastAPI data endpoints (/api/data/status, /api/data/ingest, /api/data/preview)."""
    # 1. Check initial status
    status_res = client.get("/api/data/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert "status" in status_data
    assert "has_processed_data" in status_data

    # 2. Trigger Ingest endpoint (capped at 100 rows for rapid unit test)
    ingest_res = client.post("/api/data/ingest?max_rows_per_file=100")
    assert ingest_res.status_code == 200
    ingest_data = ingest_res.json()
    assert "report" in ingest_data
    assert "number_of_source_files" in ingest_data

    # 3. Check quality endpoint
    quality_res = client.get("/api/data/quality")
    assert quality_res.status_code == 200
    quality_data = quality_res.json()
    assert "report_generated_at" in quality_data
    assert "sensor_statistics" in quality_data

    # 4. Check preview endpoint
    preview_res = client.get("/api/data/preview?limit=10")
    assert preview_res.status_code == 200
    preview_data = preview_res.json()
    assert "records" in preview_data
    assert "total_available" in preview_data
