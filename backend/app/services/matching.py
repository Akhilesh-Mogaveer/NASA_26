"""FireLens Core Spatial-Temporal Matching Service.

Orchestrates candidate generation, association processing, sensitivity evaluation,
persistence to data/matching/, and API query handling with pagination and filtering.
"""
import os
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import pandas as pd
import duckdb

from app.config import settings
from app.services.matching_config import (
    MatchingConfig,
    AssociationRecord,
    DEFAULT_SPATIAL_RADIUS_KM,
    DEFAULT_TEMPORAL_WINDOW_MINUTES,
    CANDIDATE_SPATIAL_RADII_KM,
    CANDIDATE_TEMPORAL_WINDOWS_MINUTES,
)
from app.services.candidate_generation import CandidateGenerator
from app.services.association import AssociationProcessor
from app.services.matching_evaluation import MatchingEvaluator


# Cached in-memory results for fast API responses
_CACHED_SUMMARY: Optional[Dict[str, Any]] = None
_CACHED_EVALUATION: Optional[List[Dict[str, Any]]] = None
_CACHED_METADATA: Optional[Dict[str, Any]] = None


def get_matching_dir() -> Path:
    """Return and ensure data/matching directory exists."""
    matching_dir = getattr(settings, "DATA_MATCHING_DIR", settings.DATA_DIR / "matching")
    matching_dir.mkdir(parents=True, exist_ok=True)
    return matching_dir


def clear_matching_cache() -> None:
    """Clear in-memory cached matching results."""
    global _CACHED_SUMMARY, _CACHED_EVALUATION, _CACHED_METADATA
    _CACHED_SUMMARY = None
    _CACHED_EVALUATION = None
    _CACHED_METADATA = None


def execute_matching_workflow(
    modis_df: pd.DataFrame,
    viirs_df: pd.DataFrame,
    config: Optional[MatchingConfig] = None,
    run_grid_evaluation: bool = True,
    experiment_metadata: Optional[Dict[str, Any]] = None,
    save_artifacts: bool = True,
) -> Dict[str, Any]:
    """Execute complete matching workflow: candidate generation, association, and evaluation."""
    cfg = config or MatchingConfig()
    cfg.validate()
    t_start = time.time()

    # 1. Candidate Generation
    generator = CandidateGenerator(cfg)
    raw_candidates = generator.generate_candidates(modis_df, viirs_df)
    t_candidates = time.time()

    # 2. Association & Ambiguity Classification
    processor = AssociationProcessor(cfg)
    processed = processor.process_associations(raw_candidates, modis_df, viirs_df)
    associations = processed["associations"]
    unmatched_modis = processed["unmatched_modis"]
    unmatched_viirs = processed["unmatched_viirs"]
    summary_counts = processed["summary"]
    t_association = time.time()

    # 3. Parameter Sensitivity Evaluation across all 12 combinations
    grid_results: List[Dict[str, Any]] = []
    if run_grid_evaluation:
        evaluator = MatchingEvaluator()
        grid_results = evaluator.evaluate_grid(
            modis_df,
            viirs_df,
            weight_spatial=cfg.weight_spatial,
            weight_temporal=cfg.weight_temporal,
        )
    t_evaluation = time.time()

    total_time = t_evaluation - t_start

    # Distance, Time & Score Statistics
    distances = [a.distance_km for a in associations]
    time_diffs = [a.time_diff_minutes for a in associations]
    scores = [a.heuristic_score for a in associations]

    stats = {
        "mean_distance_km": round(float(sum(distances) / max(1, len(distances))), 3) if distances else 0.0,
        "median_distance_km": round(float(pd.Series(distances).median()), 3) if distances else 0.0,
        "min_distance_km": round(float(min(distances)), 3) if distances else 0.0,
        "max_distance_km": round(float(max(distances)), 3) if distances else 0.0,
        "mean_time_diff_min": round(float(sum(time_diffs) / max(1, len(time_diffs))), 2) if time_diffs else 0.0,
        "median_time_diff_min": round(float(pd.Series(time_diffs).median()), 2) if time_diffs else 0.0,
        "mean_heuristic_score": round(float(sum(scores) / max(1, len(scores))), 3) if scores else 0.0,
    }

    # Build Summary Document
    summary_data = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "completed",
        "parameters": {
            "spatial_radius_km": cfg.spatial_radius_km,
            "temporal_window_minutes": cfg.temporal_window_minutes,
            "weight_spatial": cfg.weight_spatial,
            "weight_temporal": cfg.weight_temporal,
            "valid_only": cfg.valid_only,
            "exclude_duplicates": cfg.exclude_duplicates,
        },
        "input_counts": {
            "modis_observations_considered": len(modis_df),
            "viirs_observations_considered": len(viirs_df),
            "total_observations_considered": len(modis_df) + len(viirs_df),
        },
        "matching_results": {
            "total_candidate_associations": len(associations),
            "unique_modis_matched": summary_counts["unique_modis_matched"],
            "unique_viirs_matched": summary_counts["unique_viirs_matched"],
            "unmatched_modis_count": summary_counts["unmatched_modis_count"],
            "unmatched_viirs_count": summary_counts["unmatched_viirs_count"],
            "modis_match_rate_pct": round(summary_counts["unique_modis_matched"] / max(1, len(modis_df)) * 100.0, 2),
            "viirs_match_rate_pct": round(summary_counts["unique_viirs_matched"] / max(1, len(viirs_df)) * 100.0, 2),
            "ambiguous_modis_count": summary_counts["ambiguous_modis_count"],
            "ambiguous_viirs_count": summary_counts["ambiguous_viirs_count"],
        },
        "multiplicity_breakdown": summary_counts["multiplicity_breakdown"],
        "classification_breakdown": summary_counts["classification_breakdown"],
        "statistics": stats,
        "benchmarks": {
            "candidate_generation_seconds": round(t_candidates - t_start, 3),
            "association_processing_seconds": round(t_association - t_candidates, 3),
            "sensitivity_grid_evaluation_seconds": round(t_evaluation - t_association, 3),
            "total_processing_seconds": round(total_time, 3),
            "associations_per_second": round(len(associations) / max(0.001, total_time), 1),
        },
        "experiment_metadata": experiment_metadata or {},
    }

    # 4. Save Artifacts to data/matching/
    if save_artifacts:
        out_dir = get_matching_dir()

        # 4a. Summary JSON
        with open(out_dir / "matching_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2)

        # 4b. Sensitivity Evaluation CSV
        if grid_results:
            eval_df = pd.DataFrame(grid_results)
            eval_df.to_csv(out_dir / "matching_evaluation.csv", index=False)

        # 4c. Candidate Associations Parquet (via DuckDB)
        if associations:
            assoc_dicts = [a.to_dict() for a in associations]
            assoc_df = pd.DataFrame(assoc_dicts)
            con = duckdb.connect()
            con.register("temp_assocs", assoc_df)
            con.execute(f"COPY temp_assocs TO '{out_dir.as_posix()}/candidate_associations.parquet' (FORMAT PARQUET)")
            con.close()
        else:
            # Empty parquet placeholder
            empty_df = pd.DataFrame(columns=[
                "association_id", "modis_observation_id", "viirs_observation_id",
                "distance_km", "time_diff_minutes", "heuristic_score"
            ])
            con = duckdb.connect()
            con.register("temp_empty", empty_df)
            con.execute(f"COPY temp_empty TO '{out_dir.as_posix()}/candidate_associations.parquet' (FORMAT PARQUET)")
            con.close()

        # 4d. Unmatched Observations Parquet
        unmatched_records = []
        for r in unmatched_modis:
            unmatched_records.append({**r, "unmatched_instrument": "MODIS"})
        for r in unmatched_viirs:
            unmatched_records.append({**r, "unmatched_instrument": "VIIRS"})
        if unmatched_records:
            unmatched_df = pd.DataFrame(unmatched_records)
            con = duckdb.connect()
            con.register("temp_unmatched", unmatched_df)
            con.execute(f"COPY temp_unmatched TO '{out_dir.as_posix()}/unmatched_observations.parquet' (FORMAT PARQUET)")
            con.close()

        # 4e. Experiment Metadata JSON
        meta = {
            "software_version": "FireLens v0.1.0 (Phase 4)",
            "pipeline_stage": "Phase 4 - Spatial-Temporal Matching Engine",
            "run_timestamp": summary_data["generated_at"],
            "dataset_sources": [
                "data/processed/modis_normalized.csv",
                "data/processed/viirs_normalized.csv"
            ],
            "candidate_spatial_radii_evaluated_km": CANDIDATE_SPATIAL_RADII_KM,
            "candidate_temporal_windows_evaluated_minutes": CANDIDATE_TEMPORAL_WINDOWS_MINUTES,
            "baseline_parameters": {
                "spatial_radius_km": cfg.spatial_radius_km,
                "temporal_window_minutes": cfg.temporal_window_minutes,
                "weight_spatial": cfg.weight_spatial,
                "weight_temporal": cfg.weight_temporal,
            },
            "scientific_disclaimer": (
                "Candidate associations represent spatial and temporal proximity associations, "
                "NOT definitive proof that satellite observations correspond to the same physical fire front."
            ),
            "experiment_region_and_time": experiment_metadata or {},
        }
        with open(out_dir / "matching_experiment_metadata.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        # Clear in-memory cache to ensure fresh data
        clear_matching_cache()

    return {
        "summary": summary_data,
        "associations": associations,
        "unmatched_modis": unmatched_modis,
        "unmatched_viirs": unmatched_viirs,
        "evaluation_grid": grid_results,
    }


def get_matching_status() -> Dict[str, Any]:
    """Check whether matching artifacts exist and report status."""
    out_dir = get_matching_dir()
    summary_path = out_dir / "matching_summary.json"
    eval_path = out_dir / "matching_evaluation.csv"
    assoc_path = out_dir / "candidate_associations.parquet"

    exists = summary_path.exists() and eval_path.exists() and assoc_path.exists()
    if not exists:
        return {
            "status": "not_run",
            "message": "Matching engine has not been executed yet.",
            "artifacts_available": False,
        }

    summary = get_matching_summary()
    return {
        "status": "ready",
        "generated_at": summary.get("generated_at", ""),
        "artifacts_available": True,
        "total_associations": summary.get("matching_results", {}).get("total_candidate_associations", 0),
        "unique_modis_matched": summary.get("matching_results", {}).get("unique_modis_matched", 0),
        "unique_viirs_matched": summary.get("matching_results", {}).get("unique_viirs_matched", 0),
        "spatial_radius_km": summary.get("parameters", {}).get("spatial_radius_km", 2.0),
        "temporal_window_minutes": summary.get("parameters", {}).get("temporal_window_minutes", 60.0),
    }


def get_matching_summary() -> Dict[str, Any]:
    """Retrieve top-level matching summary document."""
    global _CACHED_SUMMARY
    if _CACHED_SUMMARY is not None:
        return _CACHED_SUMMARY

    out_dir = get_matching_dir()
    summary_path = out_dir / "matching_summary.json"
    if not summary_path.exists():
        return {}

    with open(summary_path, "r", encoding="utf-8") as f:
        _CACHED_SUMMARY = json.load(f)
    return _CACHED_SUMMARY


def get_matching_evaluation() -> List[Dict[str, Any]]:
    """Retrieve sensitivity evaluation matrix across all 12 combinations."""
    global _CACHED_EVALUATION
    if _CACHED_EVALUATION is not None:
        return _CACHED_EVALUATION

    out_dir = get_matching_dir()
    eval_path = out_dir / "matching_evaluation.csv"
    if not eval_path.exists():
        return []

    df = pd.read_csv(eval_path)
    _CACHED_EVALUATION = df.to_dict(orient="records")
    return _CACHED_EVALUATION


def get_matching_associations(
    limit: int = 50,
    offset: int = 0,
    min_score: float = 0.0,
    classification: Optional[str] = None,
    multiplicity: Optional[str] = None,
    sort_by: str = "heuristic_score",
    ascending: bool = False,
) -> Dict[str, Any]:
    """Retrieve paginated and filtered candidate associations from parquet."""
    out_dir = get_matching_dir()
    parquet_path = out_dir / "candidate_associations.parquet"
    if not parquet_path.exists():
        return {"total_count": 0, "limit": limit, "offset": offset, "items": []}

    con = duckdb.connect()
    # Build filter query
    where_clauses = [f"heuristic_score >= {float(min_score)}"]
    if classification:
        where_clauses.append(f"classification = '{classification}'")
    if multiplicity:
        where_clauses.append(f"multiplicity_type = '{multiplicity}'")
    where_sql = " AND ".join(where_clauses)

    sort_order = "ASC" if ascending else "DESC"
    valid_sorts = ["heuristic_score", "distance_km", "time_diff_minutes", "candidate_rank", "modis_frp", "viirs_frp"]
    order_col = sort_by if sort_by in valid_sorts else "heuristic_score"

    total_query = f"SELECT COUNT(*) FROM '{parquet_path.as_posix()}' WHERE {where_sql}"
    total_count = con.execute(total_query).fetchone()[0]

    data_query = f"""
        SELECT * FROM '{parquet_path.as_posix()}'
        WHERE {where_sql}
        ORDER BY {order_col} {sort_order}
        LIMIT {limit} OFFSET {offset}
    """
    df = con.execute(data_query).df()
    con.close()
    if "modis_timestamp_utc" in df.columns:
        df["modis_timestamp_utc"] = df["modis_timestamp_utc"].astype(str)
    if "viirs_timestamp_utc" in df.columns:
        df["viirs_timestamp_utc"] = df["viirs_timestamp_utc"].astype(str)
    items = df.to_dict(orient="records")

    return {
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


def get_matching_unmatched(
    instrument: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """Retrieve paginated unmatched observations from parquet."""
    out_dir = get_matching_dir()
    parquet_path = out_dir / "unmatched_observations.parquet"
    if not parquet_path.exists():
        return {"total_count": 0, "limit": limit, "offset": offset, "items": []}

    con = duckdb.connect()
    where_clause = ""
    if instrument:
        where_clause = f"WHERE unmatched_instrument = '{instrument.upper()}'"

    total_count = con.execute(f"SELECT COUNT(*) FROM '{parquet_path.as_posix()}' {where_clause}").fetchone()[0]
    data_query = f"""
        SELECT * FROM '{parquet_path.as_posix()}'
        {where_clause}
        ORDER BY timestamp_utc DESC
        LIMIT {limit} OFFSET {offset}
    """
    df = con.execute(data_query).df()
    con.close()
    if "timestamp_utc" in df.columns:
        df["timestamp_utc"] = df["timestamp_utc"].astype(str)
    items = df.to_dict(orient="records")

    return {
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "items": items,
    }
