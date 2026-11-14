"""FireLens Spatial-Temporal Matching Map Service (Phase 4.4).

Provides high-performance, server-side filtered observation points, candidate association vector lines,
observation detail lookups, and bounded summary metrics for interactive map visualization.
"""
from pathlib import Path
from typing import Dict, Any, List, Optional
import duckdb
import pandas as pd

from app.config import settings
from app.services.matching import get_matching_dir


def _get_con() -> duckdb.DuckDBPyConnection:
    """Create a configured DuckDB in-memory connection."""
    con = duckdb.connect()
    con.execute("PRAGMA memory_limit='2GB'")
    con.execute("PRAGMA threads=2")
    return con


def get_map_observations(
    min_lat: Optional[float] = None,
    max_lat: Optional[float] = None,
    min_lon: Optional[float] = None,
    max_lon: Optional[float] = None,
    sensor: str = "ALL",
    status: str = "ALL",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 500,
    offset: int = 0,
) -> Dict[str, Any]:
    """Retrieve filtered, classified observation points for interactive map rendering."""
    out_dir = get_matching_dir()
    assoc_path = out_dir / "candidate_associations.parquet"
    unmatched_path = out_dir / "unmatched_observations.parquet"

    if not assoc_path.exists() or not unmatched_path.exists():
        return {
            "total_count": 0,
            "limit": limit,
            "offset": offset,
            "items": [],
            "summary_in_bounds": {
                "total_modis": 0,
                "total_viirs": 0,
                "matched_modis": 0,
                "matched_viirs": 0,
                "ambiguous_modis": 0,
                "ambiguous_viirs": 0,
                "unmatched_modis": 0,
                "unmatched_viirs": 0,
            },
        }

    con = _get_con()
    try:
        # Build unified observation query from matched candidate associations and unmatched parquet
        matched_modis_sql = f"""
            SELECT 
                modis_observation_id AS observation_id,
                'MODIS' AS sensor,
                FIRST(modis_satellite) AS satellite,
                FIRST(modis_latitude) AS latitude,
                FIRST(modis_longitude) AS longitude,
                FIRST(CAST(modis_timestamp_utc AS VARCHAR)) AS timestamp_utc,
                FIRST(modis_frp) AS frp,
                COUNT(*) AS candidate_count,
                ROUND(MAX(heuristic_score), 4) AS top_heuristic_score,
                BOOL_OR(classification = 'ambiguous_association') AS is_ambiguous,
                CASE 
                    WHEN BOOL_OR(classification = 'ambiguous_association') THEN 'ambiguous' 
                    ELSE 'matched' 
                END AS status
            FROM '{assoc_path.as_posix()}'
            GROUP BY modis_observation_id
        """

        matched_viirs_sql = f"""
            SELECT 
                viirs_observation_id AS observation_id,
                'VIIRS' AS sensor,
                FIRST(viirs_satellite) AS satellite,
                FIRST(viirs_latitude) AS latitude,
                FIRST(viirs_longitude) AS longitude,
                FIRST(CAST(viirs_timestamp_utc AS VARCHAR)) AS timestamp_utc,
                FIRST(viirs_frp) AS frp,
                COUNT(*) AS candidate_count,
                ROUND(MAX(heuristic_score), 4) AS top_heuristic_score,
                BOOL_OR(classification = 'ambiguous_association') AS is_ambiguous,
                CASE 
                    WHEN BOOL_OR(classification = 'ambiguous_association') THEN 'ambiguous' 
                    ELSE 'matched' 
                END AS status
            FROM '{assoc_path.as_posix()}'
            GROUP BY viirs_observation_id
        """

        unmatched_sql = f"""
            SELECT 
                observation_id,
                UPPER(unmatched_instrument) AS sensor,
                satellite,
                latitude,
                longitude,
                CAST(timestamp_utc AS VARCHAR) AS timestamp_utc,
                frp,
                0 AS candidate_count,
                NULL AS top_heuristic_score,
                FALSE AS is_ambiguous,
                'unmatched' AS status
            FROM '{unmatched_path.as_posix()}'
        """

        unified_view_sql = f"""
            WITH all_obs AS (
                {matched_modis_sql}
                UNION ALL
                {matched_viirs_sql}
                UNION ALL
                {unmatched_sql}
            )
            SELECT * FROM all_obs
        """

        # Apply filtering
        where_clauses = ["1=1"]
        if min_lat is not None:
            where_clauses.append(f"latitude >= {float(min_lat)}")
        if max_lat is not None:
            where_clauses.append(f"latitude <= {float(max_lat)}")
        if min_lon is not None:
            where_clauses.append(f"longitude >= {float(min_lon)}")
        if max_lon is not None:
            where_clauses.append(f"longitude <= {float(max_lon)}")

        sensor_upper = sensor.upper().strip()
        if sensor_upper in ["MODIS", "VIIRS"]:
            where_clauses.append(f"sensor = '{sensor_upper}'")

        status_upper = status.upper().strip()
        if status_upper == "MATCHED":
            # Includes both unambiguous matched and ambiguous matched
            where_clauses.append("status IN ('matched', 'ambiguous')")
        elif status_upper == "UNMATCHED":
            where_clauses.append("status = 'unmatched'")
        elif status_upper == "AMBIGUOUS":
            where_clauses.append("is_ambiguous = TRUE")

        if start_date:
            where_clauses.append(f"SUBSTRING(timestamp_utc, 1, 10) >= '{start_date}'")
        if end_date:
            where_clauses.append(f"SUBSTRING(timestamp_utc, 1, 10) <= '{end_date}'")

        filter_sql = " AND ".join(where_clauses)

        # Count in bounds
        total_query = f"""
            WITH unified AS ({unified_view_sql})
            SELECT COUNT(*) FROM unified WHERE {filter_sql}
        """
        total_count = con.execute(total_query).fetchone()[0]

        # Aggregate summary in bounds
        summary_query = f"""
            WITH unified AS ({unified_view_sql})
            SELECT 
                COUNT(*) FILTER (WHERE sensor = 'MODIS') AS total_modis,
                COUNT(*) FILTER (WHERE sensor = 'VIIRS') AS total_viirs,
                COUNT(*) FILTER (WHERE sensor = 'MODIS' AND status IN ('matched', 'ambiguous')) AS matched_modis,
                COUNT(*) FILTER (WHERE sensor = 'VIIRS' AND status IN ('matched', 'ambiguous')) AS matched_viirs,
                COUNT(*) FILTER (WHERE sensor = 'MODIS' AND is_ambiguous = TRUE) AS ambiguous_modis,
                COUNT(*) FILTER (WHERE sensor = 'VIIRS' AND is_ambiguous = TRUE) AS ambiguous_viirs,
                COUNT(*) FILTER (WHERE sensor = 'MODIS' AND status = 'unmatched') AS unmatched_modis,
                COUNT(*) FILTER (WHERE sensor = 'VIIRS' AND status = 'unmatched') AS unmatched_viirs
            FROM unified 
            WHERE {filter_sql}
        """
        sum_row = con.execute(summary_query).fetchone()
        summary_in_bounds = {
            "total_modis": int(sum_row[0] or 0),
            "total_viirs": int(sum_row[1] or 0),
            "matched_modis": int(sum_row[2] or 0),
            "matched_viirs": int(sum_row[3] or 0),
            "ambiguous_modis": int(sum_row[4] or 0),
            "ambiguous_viirs": int(sum_row[5] or 0),
            "unmatched_modis": int(sum_row[6] or 0),
            "unmatched_viirs": int(sum_row[7] or 0),
        }

        # Data rows
        data_query = f"""
            WITH unified AS ({unified_view_sql})
            SELECT 
                observation_id, sensor, satellite, latitude, longitude, timestamp_utc,
                frp, candidate_count, top_heuristic_score, is_ambiguous, status
            FROM unified
            WHERE {filter_sql}
            ORDER BY frp DESC
            LIMIT {limit} OFFSET {offset}
        """
        df = con.execute(data_query).df()

        # Add synthetic/placeholder confidence display (to be enriched if observation detail is clicked)
        items = []
        for r in df.to_dict(orient="records"):
            items.append({
                "observation_id": str(r["observation_id"]),
                "sensor": str(r["sensor"]),
                "satellite": str(r["satellite"]),
                "latitude": float(r["latitude"]),
                "longitude": float(r["longitude"]),
                "timestamp_utc": str(r["timestamp_utc"]),
                "frp": float(r["frp"] or 0.0),
                "confidence": "See details" if r["sensor"] == "MODIS" else "nominal",
                "status": str(r["status"]),
                "is_ambiguous": bool(r["is_ambiguous"]),
                "candidate_count": int(r["candidate_count"] or 0),
                "top_heuristic_score": float(r["top_heuristic_score"]) if pd.notna(r["top_heuristic_score"]) else None,
            })

        return {
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "items": items,
            "summary_in_bounds": summary_in_bounds,
        }
    finally:
        con.close()


def get_map_lines(
    min_lat: Optional[float] = None,
    max_lat: Optional[float] = None,
    min_lon: Optional[float] = None,
    max_lon: Optional[float] = None,
    min_score: float = 0.0,
    classification: Optional[str] = None,
    multiplicity: Optional[str] = None,
    limit: int = 300,
) -> Dict[str, Any]:
    """Retrieve candidate association vector lines for interactive map rendering."""
    out_dir = get_matching_dir()
    assoc_path = out_dir / "candidate_associations.parquet"
    if not assoc_path.exists():
        return {"total_count": 0, "limit": limit, "items": []}

    con = _get_con()
    try:
        where_clauses = [f"heuristic_score >= {float(min_score)}"]

        if min_lat is not None and max_lat is not None:
            where_clauses.append(f"(modis_latitude BETWEEN {min_lat} AND {max_lat} OR viirs_latitude BETWEEN {min_lat} AND {max_lat})")
        if min_lon is not None and max_lon is not None:
            where_clauses.append(f"(modis_longitude BETWEEN {min_lon} AND {max_lon} OR viirs_longitude BETWEEN {min_lon} AND {max_lon})")

        if classification:
            where_clauses.append(f"classification = '{classification}'")
        if multiplicity:
            where_clauses.append(f"multiplicity_type = '{multiplicity}'")

        filter_sql = " AND ".join(where_clauses)

        total_count = con.execute(f"SELECT COUNT(*) FROM '{assoc_path.as_posix()}' WHERE {filter_sql}").fetchone()[0]

        data_query = f"""
            SELECT 
                association_id, modis_observation_id, viirs_observation_id,
                modis_latitude, modis_longitude, viirs_latitude, viirs_longitude,
                distance_km, time_diff_minutes, heuristic_score,
                classification, multiplicity_type, modis_frp, viirs_frp
            FROM '{assoc_path.as_posix()}'
            WHERE {filter_sql}
            ORDER BY heuristic_score DESC
            LIMIT {limit}
        """
        df = con.execute(data_query).df()

        lines = []
        for r in df.to_dict(orient="records"):
            lines.append({
                "association_id": str(r["association_id"]),
                "modis_observation_id": str(r["modis_observation_id"]),
                "viirs_observation_id": str(r["viirs_observation_id"]),
                "coordinates": [
                    [float(r["modis_latitude"]), float(r["modis_longitude"])],
                    [float(r["viirs_latitude"]), float(r["viirs_longitude"])],
                ],
                "distance_km": round(float(r["distance_km"]), 4),
                "time_diff_minutes": round(float(r["time_diff_minutes"]), 2),
                "heuristic_score": round(float(r["heuristic_score"]), 4),
                "classification": str(r["classification"]),
                "multiplicity_type": str(r["multiplicity_type"]),
                "modis_frp": round(float(r["modis_frp"]), 2),
                "viirs_frp": round(float(r["viirs_frp"]), 2),
            })

        return {
            "total_count": total_count,
            "limit": limit,
            "items": lines,
        }
    finally:
        con.close()


def get_observation_detail(observation_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve complete metadata and candidate edges for a single observation."""
    clean_id = observation_id.strip()
    is_modis = clean_id.startswith("FL-MOD")
    is_viirs = clean_id.startswith("FL-VII")

    if not is_modis and not is_viirs:
        return None

    out_dir = get_matching_dir()
    assoc_path = out_dir / "candidate_associations.parquet"
    unmatched_path = out_dir / "unmatched_observations.parquet"

    con = _get_con()
    try:
        # 1. Fetch Candidate Association Edges
        edges = []
        is_ambiguous = False
        if assoc_path.exists():
            id_col = "modis_observation_id" if is_modis else "viirs_observation_id"
            edge_query = f"""
                SELECT 
                    association_id, modis_observation_id, viirs_observation_id,
                    modis_latitude, modis_longitude, viirs_latitude, viirs_longitude,
                    modis_timestamp_utc, viirs_timestamp_utc,
                    distance_km, time_diff_minutes, heuristic_score, candidate_rank,
                    classification, multiplicity_type, modis_frp, viirs_frp,
                    modis_satellite, viirs_satellite
                FROM '{assoc_path.as_posix()}'
                WHERE {id_col} = '{clean_id}'
                ORDER BY heuristic_score DESC, distance_km ASC
            """
            edge_df = con.execute(edge_query).df()
            for r in edge_df.to_dict(orient="records"):
                if r["classification"] == "ambiguous_association":
                    is_ambiguous = True
                counterpart_id = r["viirs_observation_id"] if is_modis else r["modis_observation_id"]
                edges.append({
                    "association_id": str(r["association_id"]),
                    "counterpart_observation_id": str(counterpart_id),
                    "counterpart_sensor": "VIIRS" if is_modis else "MODIS",
                    "counterpart_satellite": str(r["viirs_satellite"] if is_modis else r["modis_satellite"]),
                    "counterpart_latitude": float(r["viirs_latitude"] if is_modis else r["modis_latitude"]),
                    "counterpart_longitude": float(r["viirs_longitude"] if is_modis else r["modis_longitude"]),
                    "counterpart_timestamp_utc": str(r["viirs_timestamp_utc"] if is_modis else r["modis_timestamp_utc"]),
                    "counterpart_frp": float(r["viirs_frp"] if is_modis else r["modis_frp"]),
                    "distance_km": round(float(r["distance_km"]), 4),
                    "time_diff_minutes": round(float(r["time_diff_minutes"]), 2),
                    "heuristic_score": round(float(r["heuristic_score"]), 4),
                    "candidate_rank": int(r["candidate_rank"]),
                    "classification": str(r["classification"]),
                    "multiplicity_type": str(r["multiplicity_type"]),
                })

        # 2. Look up observation metadata
        # Try from processed normalized files first for complete raw and validated fields
        source_file = settings.DATA_PROCESSED_DIR / ("modis_normalized.csv" if is_modis else "viirs_normalized.csv")
        obs_meta = None
        if source_file.exists():
            meta_query = f"""
                SELECT 
                    observation_id, latitude, longitude, timestamp_utc, satellite, instrument,
                    confidence, frp, brightness, scan, track, daynight
                FROM '{source_file.as_posix()}'
                WHERE observation_id = '{clean_id}'
                LIMIT 1
            """
            meta_df = con.execute(meta_query).df()
            if not meta_df.empty:
                obs_meta = meta_df.iloc[0].to_dict()

        # Fallback to unmatched or association record if processed CSV is unavailable
        if obs_meta is None and unmatched_path.exists():
            u_query = f"""
                SELECT 
                    observation_id, latitude, longitude, timestamp_utc, satellite, instrument,
                    frp, 'unmatched' as status
                FROM '{unmatched_path.as_posix()}'
                WHERE observation_id = '{clean_id}'
                LIMIT 1
            """
            u_df = con.execute(u_query).df()
            if not u_df.empty:
                obs_meta = u_df.iloc[0].to_dict()

        if obs_meta is None and edges:
            # Use edge data for fallback
            first_edge = edges[0]
            obs_meta = {
                "observation_id": clean_id,
                "satellite": first_edge["counterpart_satellite"],
                "latitude": first_edge["counterpart_latitude"],
                "longitude": first_edge["counterpart_longitude"],
                "timestamp_utc": first_edge["counterpart_timestamp_utc"],
                "frp": first_edge["counterpart_frp"],
                "instrument": "MODIS" if is_modis else "VIIRS",
                "confidence": "Unknown",
            }

        if obs_meta is None:
            return None

        status = "ambiguous" if is_ambiguous else ("matched" if len(edges) > 0 else "unmatched")

        # Format confidence safely preserving original sensor scale
        raw_conf = obs_meta.get("confidence")
        if is_modis:
            # MODIS confidence: integer percentage 0-100%
            conf_display = f"{int(float(raw_conf))}%" if pd.notna(raw_conf) else "Unknown"
        else:
            # VIIRS confidence: categorical (low, nominal, high)
            conf_display = str(raw_conf).lower() if pd.notna(raw_conf) else "nominal"

        return {
            "observation_id": clean_id,
            "sensor": "MODIS" if is_modis else "VIIRS",
            "satellite": str(obs_meta.get("satellite", "")),
            "latitude": float(obs_meta.get("latitude", 0.0)),
            "longitude": float(obs_meta.get("longitude", 0.0)),
            "timestamp_utc": str(obs_meta.get("timestamp_utc", "")),
            "frp": float(obs_meta.get("frp", 0.0) or 0.0),
            "confidence": conf_display,
            "brightness": float(obs_meta.get("brightness", 0.0)) if pd.notna(obs_meta.get("brightness")) else None,
            "scan": float(obs_meta.get("scan", 0.0)) if pd.notna(obs_meta.get("scan")) else None,
            "track": float(obs_meta.get("track", 0.0)) if pd.notna(obs_meta.get("track")) else None,
            "daynight": str(obs_meta.get("daynight", "")) if pd.notna(obs_meta.get("daynight")) else None,
            "status": status,
            "is_ambiguous": is_ambiguous,
            "candidate_count": len(edges),
            "associated_candidates": edges,
        }
    finally:
        con.close()


def get_filtered_matching_summary(
    min_lat: Optional[float] = None,
    max_lat: Optional[float] = None,
    min_lon: Optional[float] = None,
    max_lon: Optional[float] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Compute exact matching and ambiguity summary statistics for a bounded region or date range."""
    out_dir = get_matching_dir()
    assoc_path = out_dir / "candidate_associations.parquet"
    unmatched_path = out_dir / "unmatched_observations.parquet"

    empty_res = {
        "total_modis": 0,
        "total_viirs": 0,
        "total_observations": 0,
        "unique_matched_modis": 0,
        "unique_matched_viirs": 0,
        "unique_unmatched_modis": 0,
        "unique_unmatched_viirs": 0,
        "unique_ambiguous_modis": 0,
        "unique_ambiguous_viirs": 0,
        "total_candidate_edges": 0,
        "modis_match_rate_pct": 0.0,
        "viirs_match_rate_pct": 0.0,
        "mean_distance_km": 0.0,
        "mean_time_diff_min": 0.0,
        "bounds_applied": {"min_lat": min_lat, "max_lat": max_lat, "min_lon": min_lon, "max_lon": max_lon},
        "date_range_applied": {"start": start_date, "end": end_date},
    }

    if not assoc_path.exists() or not unmatched_path.exists():
        return empty_res

    con = _get_con()
    try:
        # Edge filter
        edge_clauses = ["1=1"]
        if min_lat is not None and max_lat is not None:
            edge_clauses.append(f"(modis_latitude BETWEEN {min_lat} AND {max_lat} OR viirs_latitude BETWEEN {min_lat} AND {max_lat})")
        if min_lon is not None and max_lon is not None:
            edge_clauses.append(f"(modis_longitude BETWEEN {min_lon} AND {max_lon} OR viirs_longitude BETWEEN {min_lon} AND {max_lon})")
        if start_date:
            edge_clauses.append(f"SUBSTRING(CAST(modis_timestamp_utc AS VARCHAR), 1, 10) >= '{start_date}'")
        if end_date:
            edge_clauses.append(f"SUBSTRING(CAST(modis_timestamp_utc AS VARCHAR), 1, 10) <= '{end_date}'")

        edge_sql = " AND ".join(edge_clauses)

        edge_stats_query = f"""
            SELECT 
                COUNT(*) AS total_candidate_edges,
                COUNT(DISTINCT modis_observation_id) AS matched_modis,
                COUNT(DISTINCT viirs_observation_id) AS matched_viirs,
                COUNT(DISTINCT modis_observation_id) FILTER (WHERE classification = 'ambiguous_association') AS ambiguous_modis,
                COUNT(DISTINCT viirs_observation_id) FILTER (WHERE classification = 'ambiguous_association') AS ambiguous_viirs,
                ROUND(AVG(distance_km), 3) AS mean_dist,
                ROUND(AVG(time_diff_minutes), 2) AS mean_time
            FROM '{assoc_path.as_posix()}'
            WHERE {edge_sql}
        """
        e_row = con.execute(edge_stats_query).fetchone()
        total_edges = int(e_row[0] or 0)
        matched_m = int(e_row[1] or 0)
        matched_v = int(e_row[2] or 0)
        ambig_m = int(e_row[3] or 0)
        ambig_v = int(e_row[4] or 0)
        mean_d = float(e_row[5] or 0.0)
        mean_t = float(e_row[6] or 0.0)

        # Unmatched filter
        u_clauses = ["1=1"]
        if min_lat is not None:
            u_clauses.append(f"latitude >= {min_lat}")
        if max_lat is not None:
            u_clauses.append(f"latitude <= {max_lat}")
        if min_lon is not None:
            u_clauses.append(f"longitude >= {min_lon}")
        if max_lon is not None:
            u_clauses.append(f"longitude <= {max_lon}")
        if start_date:
            u_clauses.append(f"SUBSTRING(CAST(timestamp_utc AS VARCHAR), 1, 10) >= '{start_date}'")
        if end_date:
            u_clauses.append(f"SUBSTRING(CAST(timestamp_utc AS VARCHAR), 1, 10) <= '{end_date}'")

        u_sql = " AND ".join(u_clauses)
        unmatched_stats_query = f"""
            SELECT 
                COUNT(*) FILTER (WHERE UPPER(unmatched_instrument) = 'MODIS') AS unmatched_modis,
                COUNT(*) FILTER (WHERE UPPER(unmatched_instrument) = 'VIIRS') AS unmatched_viirs
            FROM '{unmatched_path.as_posix()}'
            WHERE {u_sql}
        """
        u_row = con.execute(unmatched_stats_query).fetchone()
        unmatched_m = int(u_row[0] or 0)
        unmatched_v = int(u_row[1] or 0)

        total_m = matched_m + unmatched_m
        total_v = matched_v + unmatched_v
        total_obs = total_m + total_v

        m_rate = round((matched_m / max(1, total_m)) * 100.0, 2)
        v_rate = round((matched_v / max(1, total_v)) * 100.0, 2)

        return {
            "total_modis": total_m,
            "total_viirs": total_v,
            "total_observations": total_obs,
            "unique_matched_modis": matched_m,
            "unique_matched_viirs": matched_v,
            "unique_unmatched_modis": unmatched_m,
            "unique_unmatched_viirs": unmatched_v,
            "unique_ambiguous_modis": ambig_m,
            "unique_ambiguous_viirs": ambig_v,
            "total_candidate_edges": total_edges,
            "modis_match_rate_pct": m_rate,
            "viirs_match_rate_pct": v_rate,
            "mean_distance_km": mean_d,
            "mean_time_diff_min": mean_t,
            "bounds_applied": {"min_lat": min_lat, "max_lat": max_lat, "min_lon": min_lon, "max_lon": max_lon},
            "date_range_applied": {"start": start_date, "end": end_date},
        }
    finally:
        con.close()
