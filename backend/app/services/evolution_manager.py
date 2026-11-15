"""Evolution Manager and Persistence Service for FireLens (Phase 6).

Orchestrates temporal event evolution, track generation, lifecycle metrics,
Parquet artifact persistence in data/evolution/, background asynchronous execution,
and fast analytical queries via DuckDB.
"""

import json
import os
import time
import math
import threading
import tracemalloc
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import psutil
import duckdb
import numpy as np
import pandas as pd

from app.config import BASE_DIR, settings
from app.services.event_evolution import TemporalEventEvolutionEngine, EvolutionConfig


class EvolutionManager:
    """Singleton manager for FireLens Phase 6 temporal event evolution and lifecycle tracking."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(EvolutionManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.evolution_dir = settings.DATA_EVOLUTION_DIR
        self.evolution_dir.mkdir(parents=True, exist_ok=True)

        self.events_dir = settings.DATA_EVENTS_DIR

        # Phase 6 Artifact paths
        self.modis_relationships_file = self.evolution_dir / "modis_temporal_relationships.parquet"
        self.viirs_relationships_file = self.evolution_dir / "viirs_temporal_relationships.parquet"
        self.modis_tracks_file = self.evolution_dir / "modis_event_tracks.parquet"
        self.viirs_tracks_file = self.evolution_dir / "viirs_event_tracks.parquet"
        self.memberships_file = self.evolution_dir / "event_track_membership.parquet"
        self.lineage_file = self.evolution_dir / "event_track_lineage.parquet"
        self.summary_file = self.evolution_dir / "event_evolution_summary.json"
        self.experiments_file = self.evolution_dir / "event_evolution_experiments.parquet"
        self.manifest_file = self.evolution_dir / "event_evolution_manifest.json"

        # Background job tracking
        self._job_lock = threading.Lock()
        self.evolution_job: Dict[str, Any] = {
            "job_id": None,
            "status": "idle",
            "progress_percent": 0.0,
            "message": "No evolution job running",
            "started_at": None,
            "completed_at": None,
            "error": None,
        }

    # -------------------------------------------------------------------------
    # Execution Pipeline
    # -------------------------------------------------------------------------

    def run_evolution_sync(
        self,
        max_temporal_gap_hours: float = 24.0,
        max_spatial_distance_km: float = 5.0,
        use_extent_aware: bool = True,
        max_centroid_cap_km: float = 7.5,
        candidate_selection_strategy: str = "successive_period",
        ambiguity_delta_threshold: float = 0.15,
        experiment_name: str = "regional_boreal_evolution",
    ) -> Dict[str, Any]:
        """Execute temporal cluster continuity and event track generation synchronously."""
        t_start = time.time()
        tracemalloc.start()
        process = psutil.Process()

        config = EvolutionConfig(
            max_temporal_gap_hours=max_temporal_gap_hours,
            max_spatial_distance_km=max_spatial_distance_km,
            use_extent_aware=use_extent_aware,
            max_centroid_cap_km=max_centroid_cap_km,
            candidate_selection_strategy=candidate_selection_strategy,
            ambiguity_delta_threshold=ambiguity_delta_threshold,
        )

        engine = TemporalEventEvolutionEngine(config=config)

        # 1. Load input clusters and Phase 5 cross-sensor associations
        con = duckdb.connect()
        modis_c_path = self.events_dir / "modis_clusters.parquet"
        viirs_c_path = self.events_dir / "viirs_clusters.parquet"
        cross_assoc_path = self.events_dir / "cross_sensor_event_associations.parquet"

        if not modis_c_path.exists() or not viirs_c_path.exists():
            con.close()
            raise FileNotFoundError("Phase 5 cluster artifacts (modis_clusters.parquet, viirs_clusters.parquet) not found in data/events/")

        modis_clusters = con.execute(f"SELECT * FROM read_parquet('{modis_c_path.as_posix()}')").df().to_dict(orient="records")
        viirs_clusters = con.execute(f"SELECT * FROM read_parquet('{viirs_c_path.as_posix()}')").df().to_dict(orient="records")

        cross_assocs = []
        if cross_assoc_path.exists():
            cross_assocs = con.execute(f"SELECT * FROM read_parquet('{cross_assoc_path.as_posix()}')").df().to_dict(orient="records")

        # 2. Process MODIS temporal continuity and tracks
        modis_rels = engine.find_temporal_relationships(modis_clusters, "MODIS", cross_assocs)
        modis_tracks, modis_mems, modis_lineage = engine.build_event_tracks(modis_clusters, modis_rels, "MODIS", cross_assocs)

        # 3. Process VIIRS temporal continuity and tracks
        viirs_rels = engine.find_temporal_relationships(viirs_clusters, "VIIRS", cross_assocs)
        viirs_tracks, viirs_mems, viirs_lineage = engine.build_event_tracks(viirs_clusters, viirs_rels, "VIIRS", cross_assocs)

        # Combine memberships and lineage
        all_memberships = modis_mems + viirs_mems
        all_lineage = modis_lineage + viirs_lineage

        # 4. Save artifacts atomically via DuckDB
        temp_dir = self.evolution_dir / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Helper to write Parquet via DuckDB
        def write_parquet(records: List[Dict[str, Any]], target_file: Path, empty_schema_df: Optional[pd.DataFrame] = None):
            temp_file = temp_dir / target_file.name
            if records:
                df = pd.DataFrame(records)
            elif empty_schema_df is not None:
                df = empty_schema_df
            else:
                df = pd.DataFrame()
            
            con.register("df_to_save", df)
            con.execute(f"COPY df_to_save TO '{temp_file.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)")
            con.unregister("df_to_save")
            temp_file.replace(target_file)

        write_parquet(modis_rels, self.modis_relationships_file)
        write_parquet(viirs_rels, self.viirs_relationships_file)
        write_parquet(modis_tracks, self.modis_tracks_file)
        write_parquet(viirs_tracks, self.viirs_tracks_file)
        write_parquet(all_memberships, self.memberships_file)
        write_parquet(all_lineage, self.lineage_file)

        # Memory and runtime benchmarks
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        rss_mem = process.memory_info().rss / (1024 * 1024)
        runtime_sec = round(time.time() - t_start, 2)

        # Summary statistics calculation
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        def compute_sensor_summary(tracks: List[Dict[str, Any]], rels: List[Dict[str, Any]], clusters_count: int) -> Dict[str, Any]:
            total_tracks = len(tracks)
            multi_cluster_tracks = [t for t in tracks if t["cluster_count"] > 1]
            isolated_tracks = [t for t in tracks if t["cluster_count"] == 1]
            
            splits = sum(t["splits_count"] for t in tracks)
            merges = sum(t["merges_count"] for t in tracks)
            
            durations = [t["total_duration_hours"] for t in multi_cluster_tracks]
            median_duration = round(float(np.median(durations)), 2) if durations else 0.0
            mean_duration = round(float(np.mean(durations)), 2) if durations else 0.0
            
            class_counts: Dict[str, int] = {}
            for r in rels:
                c = r["classification"]
                class_counts[c] = class_counts.get(c, 0) + 1

            track_types: Dict[str, int] = {}
            for t in tracks:
                tt = t["track_type"]
                track_types[tt] = track_types.get(tt, 0) + 1

            total_obs = sum(t["observation_count"] for t in tracks)
            total_frp = sum(t["sum_snapshot_frp_mw"] for t in tracks)
            cross_clusters_count = sum(t.get("clusters_with_cross_sensor_evidence_count", 0) for t in tracks)
            cross_cluster_rate = round(100.0 * cross_clusters_count / max(1, clusters_count), 2)

            return {
                "clusters_represented": clusters_count,
                "total_event_tracks": total_tracks,
                "multi_cluster_tracks_count": len(multi_cluster_tracks),
                "isolated_clusters_count": len(isolated_tracks),
                "isolated_cluster_rate_pct": round(len(isolated_tracks) / max(1, total_tracks) * 100.0, 2),
                "total_temporal_relationships": len(rels),
                "splits_count": splits,
                "merges_count": merges,
                "median_observed_track_duration_hours": median_duration,
                "mean_observed_track_duration_hours": mean_duration,
                "total_observations_tracked": total_obs,
                "total_snapshot_frp_mw": round(total_frp, 2),
                "clusters_with_cross_sensor_evidence_count": cross_clusters_count,
                "cross_sensor_evidence_rate_pct": cross_cluster_rate,
                "track_type_breakdown": track_types,
                "classification_breakdown": class_counts,
            }

        modis_summary = compute_sensor_summary(modis_tracks, modis_rels, len(modis_clusters))
        viirs_summary = compute_sensor_summary(viirs_tracks, viirs_rels, len(viirs_clusters))

        # Cross-sensor supporting evidence overview
        modis_cross_ev = sum(t["cross_sensor_associations_count"] for t in modis_tracks)
        viirs_cross_ev = sum(t["cross_sensor_associations_count"] for t in viirs_tracks)

        summary: Dict[str, Any] = {
            "experiment_name": experiment_name,
            "status": "completed",
            "executed_at": now_utc,
            "parameters": {
                "max_temporal_gap_hours": max_temporal_gap_hours,
                "max_spatial_distance_km": max_spatial_distance_km,
                "use_extent_aware": use_extent_aware,
                "max_centroid_cap_km": max_centroid_cap_km,
                "candidate_selection_strategy": candidate_selection_strategy,
                "ambiguity_delta_threshold": ambiguity_delta_threshold,
            },
            "benchmarks": {
                "runtime_seconds": runtime_sec,
                "peak_traced_memory_mb": round(peak_mem / (1024 * 1024), 2),
                "process_rss_mb": round(rss_mem, 2),
                "total_clusters_processed": len(modis_clusters) + len(viirs_clusters),
                "total_relationships_generated": len(modis_rels) + len(viirs_rels),
                "total_tracks_constructed": len(modis_tracks) + len(viirs_tracks),
            },
            "modis": modis_summary,
            "viirs": viirs_summary,
            "combined_cross_sensor": {
                "phase5_cross_sensor_associations_loaded": len(cross_assocs),
                "modis_relationships_with_cross_evidence": modis_cross_ev,
                "viirs_relationships_with_cross_evidence": viirs_cross_ev,
            },
        }

        # Save summary JSON
        with open(self.summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        # Log experiment
        exp_record = {
            "experiment_name": experiment_name,
            "executed_at": now_utc,
            "max_temporal_gap_hours": max_temporal_gap_hours,
            "max_spatial_distance_km": max_spatial_distance_km,
            "modis_tracks_count": len(modis_tracks),
            "viirs_tracks_count": len(viirs_tracks),
            "modis_relationships_count": len(modis_rels),
            "viirs_relationships_count": len(viirs_rels),
            "total_splits": modis_summary["splits_count"] + viirs_summary["splits_count"],
            "total_merges": modis_summary["merges_count"] + viirs_summary["merges_count"],
            "runtime_seconds": runtime_sec,
        }
        exp_df = pd.DataFrame([exp_record])
        if self.experiments_file.exists():
            existing_exps = con.execute(f"SELECT * FROM read_parquet('{self.experiments_file.as_posix()}')").df()
            exp_df = pd.concat([existing_exps, exp_df], ignore_index=True)

        con.register("exp_to_save", exp_df)
        con.execute(f"COPY exp_to_save TO '{self.experiments_file.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        con.unregister("exp_to_save")

        # Save manifest
        manifest = {
            "last_completed_experiment": experiment_name,
            "executed_at": now_utc,
            "artifacts": {
                "modis_relationships": str(self.modis_relationships_file.relative_to(BASE_DIR)),
                "viirs_relationships": str(self.viirs_relationships_file.relative_to(BASE_DIR)),
                "modis_tracks": str(self.modis_tracks_file.relative_to(BASE_DIR)),
                "viirs_tracks": str(self.viirs_tracks_file.relative_to(BASE_DIR)),
                "memberships": str(self.memberships_file.relative_to(BASE_DIR)),
                "lineage": str(self.lineage_file.relative_to(BASE_DIR)),
                "summary": str(self.summary_file.relative_to(BASE_DIR)),
            }
        }
        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        con.close()
        return summary

    def start_evolution_job(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Start asynchronous temporal event evolution job."""
        with self._job_lock:
            if self.evolution_job["status"] == "running":
                return {
                    "status": "rejected",
                    "message": "An evolution job is already running",
                    "job_id": self.evolution_job["job_id"],
                }

            job_id = f"job-evolve-{int(time.time())}"
            self.evolution_job = {
                "job_id": job_id,
                "status": "running",
                "progress_percent": 10.0,
                "message": "Starting temporal event evolution...",
                "started_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "completed_at": None,
                "error": None,
            }

        def worker():
            try:
                with self._job_lock:
                    self.evolution_job["progress_percent"] = 30.0
                    self.evolution_job["message"] = "Processing MODIS and VIIRS cluster continuity..."

                self.run_evolution_sync(
                    max_temporal_gap_hours=params.get("max_temporal_gap_hours", 24.0),
                    max_spatial_distance_km=params.get("max_spatial_distance_km", 5.0),
                    use_extent_aware=params.get("use_extent_aware", True),
                    max_centroid_cap_km=params.get("max_centroid_cap_km", 7.5),
                    candidate_selection_strategy=params.get("candidate_selection_strategy", "successive_period"),
                    ambiguity_delta_threshold=params.get("ambiguity_delta_threshold", 0.15),
                    experiment_name=params.get("experiment_name", "regional_boreal_evolution"),
                )

                with self._job_lock:
                    self.evolution_job["status"] = "completed"
                    self.evolution_job["progress_percent"] = 100.0
                    self.evolution_job["message"] = "Temporal event evolution completed successfully"
                    self.evolution_job["completed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception as e:
                with self._job_lock:
                    self.evolution_job["status"] = "failed"
                    self.evolution_job["error"] = str(e)
                    self.evolution_job["message"] = f"Job failed: {e}"
                    self.evolution_job["completed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        t = threading.Thread(target=worker, daemon=True)
        t.start()

        return {
            "status": "accepted",
            "message": "Evolution job started in background",
            "job_id": job_id,
        }

    # -------------------------------------------------------------------------
    # Query APIs
    # -------------------------------------------------------------------------

    def get_summary(self) -> Dict[str, Any]:
        """Load latest summary JSON."""
        if not self.summary_file.exists():
            return {"status": "uninitialized", "message": "No evolution summary found. Run evolution job first."}
        with open(self.summary_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_tracks(
        self,
        sensor: Optional[str] = None,
        track_type: Optional[str] = None,
        min_clusters: int = 1,
        min_duration_hours: float = 0.0,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Query paginated event tracks."""
        files = []
        if not sensor or sensor.upper() == "ALL":
            if self.modis_tracks_file.exists():
                files.append(f"SELECT * FROM read_parquet('{self.modis_tracks_file.as_posix()}')")
            if self.viirs_tracks_file.exists():
                files.append(f"SELECT * FROM read_parquet('{self.viirs_tracks_file.as_posix()}')")
        elif sensor.upper() == "MODIS" and self.modis_tracks_file.exists():
            files.append(f"SELECT * FROM read_parquet('{self.modis_tracks_file.as_posix()}')")
        elif sensor.upper() == "VIIRS" and self.viirs_tracks_file.exists():
            files.append(f"SELECT * FROM read_parquet('{self.viirs_tracks_file.as_posix()}')")

        if not files:
            return {"items": [], "total_count": 0, "limit": limit, "offset": offset}

        union_q = " UNION ALL ".join(files)
        where_clauses = [
            f"cluster_count >= {min_clusters}",
            f"total_duration_hours >= {min_duration_hours}",
        ]
        if track_type and track_type.upper() != "ALL":
            where_clauses.append(f"track_type = '{track_type}'")

        where_str = f"WHERE {' AND '.join(where_clauses)}"

        con = duckdb.connect()
        total_q = f"SELECT COUNT(*) FROM ({union_q}) {where_str}"
        total_count = con.execute(total_q).fetchone()[0]

        data_q = f"""
            SELECT * FROM ({union_q})
            {where_str}
            ORDER BY cluster_count DESC, total_duration_hours DESC
            LIMIT {limit} OFFSET {offset}
        """
        rows = con.execute(data_q).df().to_dict(orient="records")
        con.close()

        return {
            "items": rows,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
        }

    def get_track_detail(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve single track metadata."""
        files = []
        if self.modis_tracks_file.exists():
            files.append(f"SELECT * FROM read_parquet('{self.modis_tracks_file.as_posix()}')")
        if self.viirs_tracks_file.exists():
            files.append(f"SELECT * FROM read_parquet('{self.viirs_tracks_file.as_posix()}')")
        if not files:
            return None

        union_q = " UNION ALL ".join(files)
        con = duckdb.connect()
        row = con.execute(f"SELECT * FROM ({union_q}) WHERE track_id = '{track_id}'").df().to_dict(orient="records")
        con.close()

        if not row:
            return None
        return row[0]

    def get_track_timeline(self, track_id: str) -> Dict[str, Any]:
        """Retrieve chronological timeline steps for a specific event track."""
        if not self.memberships_file.exists():
            return {"track_id": track_id, "sensor": "UNKNOWN", "total_steps": 0, "timeline": []}

        con = duckdb.connect()
        q = f"""
            SELECT * FROM read_parquet('{self.memberships_file.as_posix()}')
            WHERE track_id = '{track_id}'
            ORDER BY step_index ASC
        """
        rows = con.execute(q).df().to_dict(orient="records")
        con.close()

        if not rows:
            return {"track_id": track_id, "sensor": "UNKNOWN", "total_steps": 0, "timeline": []}

        sensor = rows[0].get("sensor", "UNKNOWN")
        timeline = []

        prev_row = None
        for r in rows:
            preds = [p for p in str(r.get("predecessors", "")).split(",") if p]
            succs = [s for s in str(r.get("successors", "")).split(",") if s]

            time_gap = None
            dist_gap = None
            frp_diff = None

            if prev_row:
                # Approximate interval to previous step
                from app.services.candidate_generation import parse_timestamp_to_epoch, haversine_distance_km
                ep_curr = parse_timestamp_to_epoch(r["timestamp_utc"]) or 0.0
                ep_prev = parse_timestamp_to_epoch(prev_row["timestamp_utc"]) or 0.0
                time_gap = round(max(0.0, (ep_curr - ep_prev) / 3600.0), 2)
                dist_gap = round(haversine_distance_km(
                    prev_row["centroid_latitude"], prev_row["centroid_longitude"],
                    r["centroid_latitude"], r["centroid_longitude"]
                ), 3)
                frp_diff = round(float(r["sum_frp_mw"]) - float(prev_row["sum_frp_mw"]), 2)

            timeline.append({
                "step_index": int(r["step_index"]),
                "cluster_id": r["cluster_id"],
                "timestamp_utc": r["timestamp_utc"],
                "duration_minutes": 0.0,
                "observation_count": int(r["observation_count"]),
                "centroid_latitude": float(r["centroid_latitude"]),
                "centroid_longitude": float(r["centroid_longitude"]),
                "sum_frp_mw": float(r["sum_frp_mw"]),
                "mean_frp_mw": round(float(r["sum_frp_mw"]) / max(1, int(r["observation_count"])), 2),
                "max_frp_mw": float(r["sum_frp_mw"]),
                "primary_satellite": str(r.get("primary_satellite", "UNKNOWN")),
                "in_degree": int(r.get("in_degree", 0)),
                "out_degree": int(r.get("out_degree", 0)),
                "predecessors": preds,
                "successors": succs,
                "has_cross_sensor_evidence": bool(r.get("has_cross_sensor_evidence", False)),
                "temporal_gap_to_prev_hours": time_gap,
                "centroid_dist_to_prev_km": dist_gap,
                "delta_frp_from_prev_mw": frp_diff,
            })
            prev_row = r

        return {
            "track_id": track_id,
            "sensor": sensor,
            "total_steps": len(timeline),
            "timeline": timeline,
        }

    def get_track_lineage(self, track_id: str) -> Dict[str, Any]:
        """Retrieve lineage graph nodes and edges for an event track."""
        if not self.lineage_file.exists():
            return {"track_id": track_id, "sensor": "UNKNOWN", "nodes": [], "edges": [], "splits_count": 0, "merges_count": 0}

        con = duckdb.connect()
        edges_q = f"""
            SELECT * FROM read_parquet('{self.lineage_file.as_posix()}')
            WHERE track_id = '{track_id}'
        """
        edge_rows = con.execute(edges_q).df().to_dict(orient="records")

        # Also get constituent nodes
        nodes_q = f"""
            SELECT * FROM read_parquet('{self.memberships_file.as_posix()}')
            WHERE track_id = '{track_id}'
            ORDER BY step_index ASC
        """
        node_rows = con.execute(nodes_q).df().to_dict(orient="records")
        con.close()

        sensor = node_rows[0].get("sensor", "UNKNOWN") if node_rows else "UNKNOWN"
        splits = sum(1 for n in node_rows if int(n.get("out_degree", 0)) > 1)
        merges = sum(1 for n in node_rows if int(n.get("in_degree", 0)) > 1)

        return {
            "track_id": track_id,
            "sensor": sensor,
            "nodes": node_rows,
            "edges": edge_rows,
            "splits_count": splits,
            "merges_count": merges,
        }

    def get_relationships(
        self,
        sensor: Optional[str] = None,
        classification: Optional[str] = None,
        min_score: float = 0.0,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Query paginated temporal continuity relationships."""
        files = []
        if not sensor or sensor.upper() == "ALL":
            if self.modis_relationships_file.exists():
                files.append(f"SELECT * FROM read_parquet('{self.modis_relationships_file.as_posix()}')")
            if self.viirs_relationships_file.exists():
                files.append(f"SELECT * FROM read_parquet('{self.viirs_relationships_file.as_posix()}')")
        elif sensor.upper() == "MODIS" and self.modis_relationships_file.exists():
            files.append(f"SELECT * FROM read_parquet('{self.modis_relationships_file.as_posix()}')")
        elif sensor.upper() == "VIIRS" and self.viirs_relationships_file.exists():
            files.append(f"SELECT * FROM read_parquet('{self.viirs_relationships_file.as_posix()}')")

        if not files:
            return {"items": [], "total_count": 0, "limit": limit, "offset": offset}

        union_q = " UNION ALL ".join(files)
        where_clauses = [f"heuristic_score >= {min_score}"]
        if classification and classification.upper() != "ALL":
            where_clauses.append(f"classification = '{classification}'")

        where_str = f"WHERE {' AND '.join(where_clauses)}"

        con = duckdb.connect()
        total_q = f"SELECT COUNT(*) FROM ({union_q}) {where_str}"
        total_count = con.execute(total_q).fetchone()[0]

        data_q = f"""
            SELECT * FROM ({union_q})
            {where_str}
            ORDER BY heuristic_score DESC, temporal_gap_hours ASC
            LIMIT {limit} OFFSET {offset}
        """
        rows = con.execute(data_q).df().to_dict(orient="records")
        con.close()

        return {
            "items": rows,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
        }

    def get_map_data(
        self,
        sensor: Optional[str] = None,
        track_id: Optional[str] = None,
        lat_min: Optional[float] = None,
        lat_max: Optional[float] = None,
        lon_min: Optional[float] = None,
        lon_max: Optional[float] = None,
        limit: int = 200,
    ) -> Dict[str, Any]:
        """Retrieve map nodes (cluster centroids) and directed edges for Leaflet map display."""
        if not self.memberships_file.exists() or not self.modis_relationships_file.exists():
            return {"nodes": [], "edges": [], "nodes_count": 0, "edges_count": 0}

        con = duckdb.connect()

        # Build node query
        where_nodes = []
        if sensor and sensor.upper() != "ALL":
            where_nodes.append(f"m.sensor = '{sensor.upper()}'")
        if track_id:
            where_nodes.append(f"m.track_id = '{track_id}'")
        if lat_min is not None and lat_max is not None:
            where_nodes.append(f"m.centroid_latitude >= {lat_min} AND m.centroid_latitude <= {lat_max}")
        if lon_min is not None and lon_max is not None:
            where_nodes.append(f"m.centroid_longitude >= {lon_min} AND m.centroid_longitude <= {lon_max}")

        where_nodes_str = f"WHERE {' AND '.join(where_nodes)}" if where_nodes else ""

        # Join with track to get track_type
        tracks_union = []
        if self.modis_tracks_file.exists():
            tracks_union.append(f"SELECT track_id, track_type FROM read_parquet('{self.modis_tracks_file.as_posix()}')")
        if self.viirs_tracks_file.exists():
            tracks_union.append(f"SELECT track_id, track_type FROM read_parquet('{self.viirs_tracks_file.as_posix()}')")
        
        tracks_q = " UNION ALL ".join(tracks_union) if tracks_union else "SELECT '' as track_id, '' as track_type WHERE 1=0"

        nodes_q = f"""
            SELECT 
                m.cluster_id, m.track_id, m.sensor,
                m.centroid_latitude as latitude, m.centroid_longitude as longitude,
                m.timestamp_utc, m.observation_count, m.sum_frp_mw,
                COALESCE(t.track_type, 'isolated_cluster') as track_type
            FROM read_parquet('{self.memberships_file.as_posix()}') m
            LEFT JOIN ({tracks_q}) t ON m.track_id = t.track_id
            {where_nodes_str}
            LIMIT {limit}
        """
        nodes = con.execute(nodes_q).df().to_dict(orient="records")

        # Build edge query
        rel_files = []
        if not sensor or sensor.upper() == "ALL":
            if self.modis_relationships_file.exists():
                rel_files.append(f"SELECT * FROM read_parquet('{self.modis_relationships_file.as_posix()}')")
            if self.viirs_relationships_file.exists():
                rel_files.append(f"SELECT * FROM read_parquet('{self.viirs_relationships_file.as_posix()}')")
        elif sensor.upper() == "MODIS" and self.modis_relationships_file.exists():
            rel_files.append(f"SELECT * FROM read_parquet('{self.modis_relationships_file.as_posix()}')")
        elif sensor.upper() == "VIIRS" and self.viirs_relationships_file.exists():
            rel_files.append(f"SELECT * FROM read_parquet('{self.viirs_relationships_file.as_posix()}')")

        edges = []
        if rel_files:
            union_rels = " UNION ALL ".join(rel_files)
            where_edges = []
            if track_id:
                where_edges.append(f"track_id = '{track_id}'")
            if lat_min is not None and lat_max is not None:
                where_edges.append(f"source_centroid_lat >= {lat_min} AND source_centroid_lat <= {lat_max}")
            if lon_min is not None and lon_max is not None:
                where_edges.append(f"source_centroid_lon >= {lon_min} AND source_centroid_lon <= {lon_max}")

            where_edges_str = f"WHERE {' AND '.join(where_edges)}" if where_edges else ""

            edges_q = f"""
                SELECT 
                    relationship_id, COALESCE(track_id, 'UNKNOWN') as track_id, sensor,
                    source_cluster_id, target_cluster_id,
                    source_centroid_lat, source_centroid_lon,
                    target_centroid_lat, target_centroid_lon,
                    temporal_gap_hours, centroid_distance_km,
                    classification, heuristic_score, is_ambiguous
                FROM ({union_rels})
                {where_edges_str}
                LIMIT {limit}
            """
            edge_rows = con.execute(edges_q).df().to_dict(orient="records")
            for er in edge_rows:
                edges.append({
                    "relationship_id": er["relationship_id"],
                    "track_id": er["track_id"],
                    "sensor": er["sensor"],
                    "source_cluster_id": er["source_cluster_id"],
                    "target_cluster_id": er["target_cluster_id"],
                    "coordinates": [
                        [float(er["source_centroid_lat"]), float(er["source_centroid_lon"])],
                        [float(er["target_centroid_lat"]), float(er["target_centroid_lon"])],
                    ],
                    "temporal_gap_hours": float(er["temporal_gap_hours"]),
                    "centroid_distance_km": float(er["centroid_distance_km"]),
                    "classification": er["classification"],
                    "heuristic_score": float(er["heuristic_score"]),
                    "is_ambiguous": bool(er["is_ambiguous"]),
                })

        con.close()

        return {
            "nodes": nodes,
            "edges": edges,
            "nodes_count": len(nodes),
            "edges_count": len(edges),
        }

    def get_experiments(self) -> List[Dict[str, Any]]:
        """Retrieve historical evolution experiment records."""
        if not self.experiments_file.exists():
            return []
        con = duckdb.connect()
        rows = con.execute(f"SELECT * FROM read_parquet('{self.experiments_file.as_posix()}') ORDER BY executed_at DESC").df().to_dict(orient="records")
        con.close()
        return rows


evolution_manager = EvolutionManager()
