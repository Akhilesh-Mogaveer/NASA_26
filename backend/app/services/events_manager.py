"""Events Manager and Persistence Service for FireLens.

Orchestrates independent fire event clustering (Phase 5.1), cross-sensor event association (Phase 5.2),
Parquet artifact persistence in data/events/, background execution, and fast analytical query services.
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

from app.config import settings
from app.services.clustering import SpatialTemporalDBSCAN, PartitionedClusteringEngine
from app.services.event_association import CrossSensorEventAssociator


class EventsManager:
    """Singleton manager for FireLens Phase 5.1 & Phase 5.2 event clustering and association."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(EventsManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.events_dir = settings.DATA_EVENTS_DIR
        self.events_dir.mkdir(parents=True, exist_ok=True)

        self.modis_clusters_file = self.events_dir / "modis_clusters.parquet"
        self.viirs_clusters_file = self.events_dir / "viirs_clusters.parquet"
        self.modis_membership_file = self.events_dir / "modis_cluster_membership.parquet"
        self.viirs_membership_file = self.events_dir / "viirs_cluster_membership.parquet"
        self.noise_file = self.events_dir / "cluster_noise_observations.parquet"
        self.associations_file = self.events_dir / "cross_sensor_event_associations.parquet"
        self.components_file = self.events_dir / "event_relationship_components.parquet"
        self.clustering_summary_file = self.events_dir / "clustering_summary.json"
        self.association_summary_file = self.events_dir / "event_association_summary.json"
        self.experiments_file = self.events_dir / "clustering_experiments.parquet"
        self.manifest_file = self.events_dir / "event_processing_manifest.json"

        # Background job tracking
        self._job_lock = threading.Lock()
        self.clustering_job: Dict[str, Any] = {
            "job_id": None,
            "status": "idle",
            "progress_percent": 0.0,
            "message": "No clustering job running",
            "started_at": None,
            "completed_at": None,
            "error": None,
        }
        self.association_job: Dict[str, Any] = {
            "job_id": None,
            "status": "idle",
            "progress_percent": 0.0,
            "message": "No association job running",
            "started_at": None,
            "completed_at": None,
            "error": None,
        }

    # -------------------------------------------------------------------------
    # Phase 5.1: Independent Event Clustering Pipeline
    # -------------------------------------------------------------------------
    def run_clustering_sync(
        self,
        spatial_radius_km: float = 2.0,
        temporal_window_minutes: float = 60.0,
        min_samples: int = 3,
        bounds: Optional[Dict[str, float]] = None,
        date_range: Optional[Tuple[str, str]] = None,
        experiment_name: str = "regional_boreal_baseline",
    ) -> Dict[str, Any]:
        """Execute independent clustering for MODIS and VIIRS synchronously."""
        t_start = time.time()
        tracemalloc.start()
        process = psutil.Process()

        # Connect to DuckDB for fast data loading
        con = duckdb.connect()
        con.execute("PRAGMA memory_limit='3GB'")
        con.execute("PRAGMA threads=2")

        # Bounds filter
        b_filter = ""
        if bounds:
            b_filter = f"""
                AND latitude >= {bounds['lat_min']} AND latitude <= {bounds['lat_max']}
                AND longitude >= {bounds['lon_min']} AND longitude <= {bounds['lon_max']}
            """

        d_filter = ""
        if date_range:
            d_filter = f"AND acquisition_date >= '{date_range[0]}' AND acquisition_date <= '{date_range[1]}'"

        modis_csv = settings.DATA_PROCESSED_DIR / "modis_normalized.csv"
        viirs_csv = settings.DATA_PROCESSED_DIR / "viirs_normalized.csv"

        # If bounds or date_range are not specified, default to Saskatchewan Boreal benchmark (Aug 1-2, 2025)
        # to align with Phase 4 candidate associations
        if not bounds and not date_range:
            b_filter = "AND latitude >= 54.0 AND latitude <= 58.0 AND longitude >= -106.0 AND longitude <= -102.0"
            d_filter = "AND acquisition_date >= '2025-08-01' AND acquisition_date <= '2025-08-02'"

        # 1. Load MODIS Observations
        q_modis = f"""
            SELECT 
                observation_id, latitude, longitude, timestamp_utc, acquisition_date,
                satellite, instrument, confidence, frp, brightness, scan, track, daynight
            FROM read_csv('{modis_csv.as_posix()}')
            WHERE is_valid = true
              {b_filter}
              {d_filter}
        """
        m_df = con.execute(q_modis).df().reset_index(drop=True)

        # 2. Load VIIRS Observations
        q_viirs = f"""
            SELECT 
                observation_id, latitude, longitude, timestamp_utc, acquisition_date,
                satellite, instrument, confidence, frp, brightness, scan, track, daynight
            FROM read_csv('{viirs_csv.as_posix()}')
            WHERE is_valid = true
              {b_filter}
              {d_filter}
        """
        v_df = con.execute(q_viirs).df().reset_index(drop=True)
        con.close()

        # 3. Independent MODIS Clustering
        modis_engine = SpatialTemporalDBSCAN(
            spatial_radius_km=spatial_radius_km,
            temporal_window_minutes=temporal_window_minutes,
            min_samples=min_samples,
            sensor="MODIS",
        )
        m_clusters, m_memberships, m_noise = modis_engine.fit(m_df)

        # 4. Independent VIIRS Clustering
        viirs_engine = SpatialTemporalDBSCAN(
            spatial_radius_km=spatial_radius_km,
            temporal_window_minutes=temporal_window_minutes,
            min_samples=min_samples,
            sensor="VIIRS",
        )
        v_clusters, v_memberships, v_noise = viirs_engine.fit(v_df)

        # Combine noise
        all_noise = m_noise + v_noise

        # 5. Persist Parquet Artifacts atomically using DuckDB
        con_w = duckdb.connect()

        # MODIS Clusters
        if m_clusters:
            m_c_df = pd.DataFrame(m_clusters)
            con_w.register("temp_mc", m_c_df)
            con_w.execute(f"COPY temp_mc TO '{self.modis_clusters_file.as_posix()}' (FORMAT PARQUET)")
        else:
            self._write_empty_clusters(self.modis_clusters_file, "MODIS")

        # VIIRS Clusters
        if v_clusters:
            v_c_df = pd.DataFrame(v_clusters)
            con_w.register("temp_vc", v_c_df)
            con_w.execute(f"COPY temp_vc TO '{self.viirs_clusters_file.as_posix()}' (FORMAT PARQUET)")
        else:
            self._write_empty_clusters(self.viirs_clusters_file, "VIIRS")

        # MODIS Memberships
        if m_memberships:
            m_m_df = pd.DataFrame(m_memberships)
            con_w.register("temp_mm", m_m_df)
            con_w.execute(f"COPY temp_mm TO '{self.modis_membership_file.as_posix()}' (FORMAT PARQUET)")
        else:
            self._write_empty_memberships(self.modis_membership_file)

        # VIIRS Memberships
        if v_memberships:
            v_m_df = pd.DataFrame(v_memberships)
            con_w.register("temp_vm", v_m_df)
            con_w.execute(f"COPY temp_vm TO '{self.viirs_membership_file.as_posix()}' (FORMAT PARQUET)")
        else:
            self._write_empty_memberships(self.viirs_membership_file)

        # Noise Observations
        if all_noise:
            noise_df = pd.DataFrame(all_noise)
            con_w.register("temp_noise", noise_df)
            con_w.execute(f"COPY temp_noise TO '{self.noise_file.as_posix()}' (FORMAT PARQUET)")
        else:
            self._write_empty_memberships(self.noise_file)

        con_w.close()

        # Profile memory and runtime
        elapsed_sec = round(time.time() - t_start, 2)
        _, peak_mem_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_traced_mb = round(peak_mem_bytes / (1024 * 1024), 2)
        rss_mb = round(process.memory_info().rss / (1024 * 1024), 2)

        # 6. Save Clustering Summary JSON
        summary = {
            "experiment_name": experiment_name,
            "status": "completed",
            "executed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "parameters": {
                "spatial_radius_km": spatial_radius_km,
                "temporal_window_minutes": temporal_window_minutes,
                "min_samples": min_samples,
            },
            "bounds": bounds or {"lat_min": 54.0, "lat_max": 58.0, "lon_min": -106.0, "lon_max": -102.0},
            "date_range": date_range or ["2025-08-01", "2025-08-02"],
            "benchmarks": {
                "runtime_seconds": elapsed_sec,
                "peak_traced_memory_mb": peak_traced_mb,
                "process_rss_mb": rss_mb,
                "total_observations_processed": len(m_df) + len(v_df),
                "throughput_obs_per_sec": round((len(m_df) + len(v_df)) / max(0.001, elapsed_sec), 1),
            },
            "modis": {
                "input_observations": len(m_df),
                "cluster_count": len(m_clusters),
                "clustered_observations": len(m_memberships),
                "noise_observations": len(m_noise),
                "clustering_rate_pct": round((len(m_memberships) / max(1, len(m_df))) * 100.0, 2),
                "noise_rate_pct": round((len(m_noise) / max(1, len(m_df))) * 100.0, 2),
                "avg_observations_per_cluster": round(len(m_memberships) / max(1, len(m_clusters)), 2),
                "total_snapshot_frp_mw": round(float(sum(c["sum_frp_mw"] for c in m_clusters)), 2),
            },
            "viirs": {
                "input_observations": len(v_df),
                "cluster_count": len(v_clusters),
                "clustered_observations": len(v_memberships),
                "noise_observations": len(v_noise),
                "clustering_rate_pct": round((len(v_memberships) / max(1, len(v_df))) * 100.0, 2),
                "noise_rate_pct": round((len(v_noise) / max(1, len(v_df))) * 100.0, 2),
                "avg_observations_per_cluster": round(len(v_memberships) / max(1, len(v_clusters)), 2),
                "total_snapshot_frp_mw": round(float(sum(c["sum_frp_mw"] for c in v_clusters)), 2),
            },
        }

        with open(self.clustering_summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        # 7. Append to clustering experiments log
        self._record_clustering_experiment(summary)

        return summary

    def _write_empty_clusters(self, path: Path, sensor: str):
        empty_df = pd.DataFrame(columns=[
            "cluster_id", "sensor", "observation_count", "core_count", "border_count",
            "centroid_latitude", "centroid_longitude", "min_latitude", "max_latitude",
            "min_longitude", "max_longitude", "start_timestamp_utc", "end_timestamp_utc",
            "duration_minutes", "mean_spatial_spread_km", "max_spatial_spread_km",
            "sum_frp_mw", "mean_frp_mw", "max_frp_mw", "primary_satellite"
        ])
        con = duckdb.connect()
        con.register("empty_c", empty_df)
        con.execute(f"COPY empty_c TO '{path.as_posix()}' (FORMAT PARQUET)")
        con.close()

    def _write_empty_memberships(self, path: Path):
        empty_df = pd.DataFrame(columns=[
            "observation_id", "cluster_id", "sensor", "point_role",
            "latitude", "longitude", "timestamp_utc", "frp", "satellite"
        ])
        con = duckdb.connect()
        con.register("empty_m", empty_df)
        con.execute(f"COPY empty_m TO '{path.as_posix()}' (FORMAT PARQUET)")
        con.close()

    def _record_clustering_experiment(self, summary: Dict[str, Any]):
        exp_row = {
            "experiment_name": summary["experiment_name"],
            "executed_at": summary["executed_at"],
            "spatial_radius_km": summary["parameters"]["spatial_radius_km"],
            "temporal_window_minutes": summary["parameters"]["temporal_window_minutes"],
            "min_samples": summary["parameters"]["min_samples"],
            "modis_obs": summary["modis"]["input_observations"],
            "modis_clusters": summary["modis"]["cluster_count"],
            "modis_noise": summary["modis"]["noise_observations"],
            "viirs_obs": summary["viirs"]["input_observations"],
            "viirs_clusters": summary["viirs"]["cluster_count"],
            "viirs_noise": summary["viirs"]["noise_observations"],
            "runtime_seconds": summary["benchmarks"]["runtime_seconds"],
            "peak_memory_mb": summary["benchmarks"]["peak_traced_memory_mb"],
        }
        exp_df = pd.DataFrame([exp_row])
        con = duckdb.connect()
        if self.experiments_file.exists():
            con.execute(f"""
                CREATE TABLE prev AS SELECT * FROM read_parquet('{self.experiments_file.as_posix()}');
                INSERT INTO prev SELECT * FROM exp_df;
                COPY prev TO '{self.experiments_file.as_posix()}' (FORMAT PARQUET);
            """)
        else:
            con.register("exp_init", exp_df)
            con.execute(f"COPY exp_init TO '{self.experiments_file.as_posix()}' (FORMAT PARQUET)")
        con.close()

    # -------------------------------------------------------------------------
    # Phase 5.2: Cross-Sensor Event Association Pipeline
    # -------------------------------------------------------------------------
    def run_association_sync(
        self,
        min_supporting_pairs: int = 1,
        ambiguity_delta_threshold: float = 0.15,
    ) -> Dict[str, Any]:
        """Execute cross-sensor event association linking MODIS and VIIRS clusters."""
        if not self.modis_clusters_file.exists() or not self.viirs_clusters_file.exists():
            raise FileNotFoundError("Clustering artifacts not found. Please run clustering first.")

        con = duckdb.connect()
        con.execute("PRAGMA memory_limit='3GB'")
        con.execute("PRAGMA threads=2")

        # Load clusters and memberships
        m_clusters = con.execute(f"SELECT * FROM read_parquet('{self.modis_clusters_file.as_posix()}')").df().to_dict(orient="records")
        v_clusters = con.execute(f"SELECT * FROM read_parquet('{self.viirs_clusters_file.as_posix()}')").df().to_dict(orient="records")
        m_members = con.execute(f"SELECT * FROM read_parquet('{self.modis_membership_file.as_posix()}')").df().to_dict(orient="records")
        v_members = con.execute(f"SELECT * FROM read_parquet('{self.viirs_membership_file.as_posix()}')").df().to_dict(orient="records")

        # Load Phase 4 candidate associations
        cand_parquet = settings.DATA_MATCHING_DIR / "candidate_associations.parquet"
        if not cand_parquet.exists():
            con.close()
            raise FileNotFoundError(f"Candidate associations not found at {cand_parquet}")

        cand_df = con.execute(f"""
            SELECT 
                modis_observation_id, viirs_observation_id,
                distance_km, time_diff_minutes, heuristic_score
            FROM read_parquet('{cand_parquet.as_posix()}')
        """).df()
        con.close()

        # Run event association
        associator = CrossSensorEventAssociator(
            spatial_radius_km=2.0,
            temporal_window_minutes=60.0,
            min_supporting_pairs=min_supporting_pairs,
            ambiguity_delta_threshold=ambiguity_delta_threshold,
        )

        relationships, components, summary = associator.associate_clusters(
            modis_clusters=m_clusters,
            viirs_clusters=v_clusters,
            modis_memberships=m_members,
            viirs_memberships=v_members,
            candidate_associations_df=cand_df,
        )

        # Persist Relationships and Components Parquet
        con_w = duckdb.connect()
        if relationships:
            rel_df = pd.DataFrame(relationships)
            con_w.register("temp_rels", rel_df)
            con_w.execute(f"COPY temp_rels TO '{self.associations_file.as_posix()}' (FORMAT PARQUET)")
        else:
            empty_rel = pd.DataFrame(columns=[
                "relationship_id", "modis_cluster_id", "viirs_cluster_id", "supporting_pairs_count",
                "unique_supporting_modis_obs", "unique_supporting_viirs_obs", "heuristic_event_score",
                "multiplicity_type", "classification", "is_ambiguous"
            ])
            con_w.register("empty_rel", empty_rel)
            con_w.execute(f"COPY empty_rel TO '{self.associations_file.as_posix()}' (FORMAT PARQUET)")

        if components:
            comp_df = pd.DataFrame(components)
            # Serialize list columns to JSON strings for standard Parquet compatibility
            comp_df["modis_cluster_ids"] = comp_df["modis_cluster_ids"].apply(json.dumps)
            comp_df["viirs_cluster_ids"] = comp_df["viirs_cluster_ids"].apply(json.dumps)
            comp_df["relationship_ids"] = comp_df["relationship_ids"].apply(json.dumps)
            con_w.register("temp_comps", comp_df)
            con_w.execute(f"COPY temp_comps TO '{self.components_file.as_posix()}' (FORMAT PARQUET)")
        else:
            empty_comp = pd.DataFrame(columns=[
                "component_id", "topology_type", "modis_clusters_count", "viirs_clusters_count",
                "relationship_edges_count", "total_supporting_pairs", "is_ambiguous"
            ])
            con_w.register("empty_comp", empty_comp)
            con_w.execute(f"COPY empty_comp TO '{self.components_file.as_posix()}' (FORMAT PARQUET)")

        con_w.close()

        # Save summary JSON
        with open(self.association_summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        # Update manifest
        manifest = {
            "last_association_run": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "relationships_generated": len(relationships),
            "connected_components_generated": len(components),
            "status": "completed",
        }
        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return summary

    # -------------------------------------------------------------------------
    # Asynchronous Job Execution
    # -------------------------------------------------------------------------
    def start_clustering_job(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Start an asynchronous clustering job."""
        with self._job_lock:
            if self.clustering_job["status"] == "running":
                return {"status": "rejected", "message": "A clustering job is already running"}

            job_id = f"JOB-CLUST-{int(time.time())}"
            self.clustering_job = {
                "job_id": job_id,
                "status": "running",
                "progress_percent": 10.0,
                "message": "Initializing spatial-temporal clustering...",
                "started_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "completed_at": None,
                "error": None,
            }

            thread = threading.Thread(
                target=self._run_clustering_worker,
                args=(params,),
                daemon=True,
            )
            thread.start()
            return {"status": "started", "job_id": job_id}

    def _run_clustering_worker(self, params: Dict[str, Any]):
        try:
            self.clustering_job["progress_percent"] = 30.0
            self.clustering_job["message"] = "Processing MODIS & VIIRS active fire observations..."
            summary = self.run_clustering_sync(
                spatial_radius_km=params.get("spatial_radius_km", 2.0),
                temporal_window_minutes=params.get("temporal_window_minutes", 60.0),
                min_samples=params.get("min_samples", 3),
                bounds=params.get("bounds"),
                date_range=params.get("date_range"),
                experiment_name=params.get("experiment_name", "user_initiated_run"),
            )
            self.clustering_job["status"] = "completed"
            self.clustering_job["progress_percent"] = 100.0
            self.clustering_job["completed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            self.clustering_job["message"] = (
                f"Clustering complete. {summary['modis']['cluster_count']} MODIS clusters, "
                f"{summary['viirs']['cluster_count']} VIIRS clusters."
            )
        except Exception as e:
            self.clustering_job["status"] = "failed"
            self.clustering_job["error"] = str(e)
            self.clustering_job["message"] = f"Clustering failed: {e}"

    def start_association_job(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Start an asynchronous cross-sensor event association job."""
        with self._job_lock:
            if self.association_job["status"] == "running":
                return {"status": "rejected", "message": "An association job is already running"}

            job_id = f"JOB-ASSOC-{int(time.time())}"
            self.association_job = {
                "job_id": job_id,
                "status": "running",
                "progress_percent": 15.0,
                "message": "Initializing cross-sensor cluster association...",
                "started_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "completed_at": None,
                "error": None,
            }

            thread = threading.Thread(
                target=self._run_association_worker,
                args=(params,),
                daemon=True,
            )
            thread.start()
            return {"status": "started", "job_id": job_id}

    def _run_association_worker(self, params: Dict[str, Any]):
        try:
            self.association_job["progress_percent"] = 40.0
            self.association_job["message"] = "Aggregating Phase 4 observation candidate edges by cluster pair..."
            summary = self.run_association_sync(
                min_supporting_pairs=params.get("min_supporting_pairs", 1),
                ambiguity_delta_threshold=params.get("ambiguity_delta_threshold", 0.15),
            )
            self.association_job["status"] = "completed"
            self.association_job["progress_percent"] = 100.0
            self.association_job["completed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            self.association_job["message"] = (
                f"Event association complete. {summary['total_candidate_relationships']} candidate cluster relationships found."
            )
        except Exception as e:
            self.association_job["status"] = "failed"
            self.association_job["error"] = str(e)
            self.association_job["message"] = f"Event association failed: {e}"

    # -------------------------------------------------------------------------
    # Analytical Queries for Backend API
    # -------------------------------------------------------------------------
    def get_clustering_summary(self) -> Dict[str, Any]:
        """Return the latest clustering summary."""
        if self.clustering_summary_file.exists():
            with open(self.clustering_summary_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"status": "uninitialized", "message": "No clustering summary found"}

    def get_association_summary(self) -> Dict[str, Any]:
        """Return the latest event association summary."""
        if self.association_summary_file.exists():
            with open(self.association_summary_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"status": "uninitialized", "message": "No association summary found"}

    def get_clusters(
        self,
        sensor: Optional[str] = None,
        min_obs: int = 1,
        lat_min: Optional[float] = None,
        lat_max: Optional[float] = None,
        lon_min: Optional[float] = None,
        lon_max: Optional[float] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Query paginated clusters across sensors."""
        files = []
        if not sensor or sensor.upper() == "ALL":
            if self.modis_clusters_file.exists():
                files.append(f"SELECT * FROM read_parquet('{self.modis_clusters_file.as_posix()}')")
            if self.viirs_clusters_file.exists():
                files.append(f"SELECT * FROM read_parquet('{self.viirs_clusters_file.as_posix()}')")
        elif sensor.upper() == "MODIS" and self.modis_clusters_file.exists():
            files.append(f"SELECT * FROM read_parquet('{self.modis_clusters_file.as_posix()}')")
        elif sensor.upper() == "VIIRS" and self.viirs_clusters_file.exists():
            files.append(f"SELECT * FROM read_parquet('{self.viirs_clusters_file.as_posix()}')")

        if not files:
            return {"items": [], "total_count": 0, "limit": limit, "offset": offset}

        union_q = " UNION ALL ".join(files)
        where_clauses = [f"observation_count >= {min_obs}"]

        if lat_min is not None and lat_max is not None:
            where_clauses.append(f"centroid_latitude >= {lat_min} AND centroid_latitude <= {lat_max}")
        if lon_min is not None and lon_max is not None:
            where_clauses.append(f"centroid_longitude >= {lon_min} AND centroid_longitude <= {lon_max}")

        where_str = f"WHERE {' AND '.join(where_clauses)}"

        con = duckdb.connect()
        total_q = f"SELECT COUNT(*) FROM ({union_q}) AS u {where_str}"
        total_count = con.execute(total_q).fetchone()[0]

        data_q = f"""
            SELECT * FROM ({union_q}) AS u
            {where_str}
            ORDER BY observation_count DESC, start_timestamp_utc DESC
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

    def get_cluster_detail(self, cluster_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full details of a specific cluster."""
        target_file = None
        if "MODIS" in cluster_id.upper() and self.modis_clusters_file.exists():
            target_file = self.modis_clusters_file
        elif "VIIRS" in cluster_id.upper() and self.viirs_clusters_file.exists():
            target_file = self.viirs_clusters_file
        else:
            # Try both
            for f in [self.modis_clusters_file, self.viirs_clusters_file]:
                if f.exists():
                    con = duckdb.connect()
                    cnt = con.execute(f"SELECT COUNT(*) FROM read_parquet('{f.as_posix()}') WHERE cluster_id = '{cluster_id}'").fetchone()[0]
                    con.close()
                    if cnt > 0:
                        target_file = f
                        break

        if not target_file:
            return None

        con = duckdb.connect()
        row = con.execute(f"SELECT * FROM read_parquet('{target_file.as_posix()}') WHERE cluster_id = '{cluster_id}'").df().to_dict(orient="records")
        con.close()

        if not row:
            return None
        return row[0]

    def get_cluster_observations(self, cluster_id: str, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Retrieve observations belonging to a specific cluster."""
        m_file = self.modis_membership_file
        v_file = self.viirs_membership_file

        files = []
        if "MODIS" in cluster_id.upper() and m_file.exists():
            files.append(m_file)
        elif "VIIRS" in cluster_id.upper() and v_file.exists():
            files.append(v_file)
        else:
            files = [f for f in [m_file, v_file] if f.exists()]

        if not files:
            return {"observations": [], "total_count": 0}

        union_q = " UNION ALL ".join([f"SELECT * FROM read_parquet('{f.as_posix()}')" for f in files])

        con = duckdb.connect()
        total_q = f"SELECT COUNT(*) FROM ({union_q}) AS u WHERE cluster_id = '{cluster_id}'"
        total_count = con.execute(total_q).fetchone()[0]

        data_q = f"""
            SELECT * FROM ({union_q}) AS u
            WHERE cluster_id = '{cluster_id}'
            ORDER BY timestamp_utc ASC
            LIMIT {limit} OFFSET {offset}
        """
        rows = con.execute(data_q).df().to_dict(orient="records")
        con.close()

        return {
            "cluster_id": cluster_id,
            "observations": rows,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
        }

    def get_relationships(
        self,
        multiplicity: Optional[str] = None,
        classification: Optional[str] = None,
        min_score: float = 0.0,
        lat_min: Optional[float] = None,
        lat_max: Optional[float] = None,
        lon_min: Optional[float] = None,
        lon_max: Optional[float] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Query paginated cross-sensor cluster relationships."""
        if not self.associations_file.exists():
            return {"items": [], "total_count": 0, "limit": limit, "offset": offset}

        where_clauses = [f"heuristic_event_score >= {min_score}"]

        if multiplicity and multiplicity.upper() != "ALL":
            where_clauses.append(f"multiplicity_type = '{multiplicity}'")
        if classification and classification.upper() != "ALL":
            where_clauses.append(f"classification = '{classification}'")

        if lat_min is not None and lat_max is not None:
            where_clauses.append(f"modis_centroid_lat >= {lat_min} AND modis_centroid_lat <= {lat_max}")
        if lon_min is not None and lon_max is not None:
            where_clauses.append(f"modis_centroid_lon >= {lon_min} AND modis_centroid_lon <= {lon_max}")

        where_str = f"WHERE {' AND '.join(where_clauses)}"

        con = duckdb.connect()
        total_q = f"SELECT COUNT(*) FROM read_parquet('{self.associations_file.as_posix()}') {where_str}"
        total_count = con.execute(total_q).fetchone()[0]

        data_q = f"""
            SELECT * FROM read_parquet('{self.associations_file.as_posix()}')
            {where_str}
            ORDER BY heuristic_event_score DESC, supporting_pairs_count DESC
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

    def get_relationship_detail(self, relationship_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full details of a specific cross-sensor cluster relationship."""
        if not self.associations_file.exists():
            return None

        con = duckdb.connect()
        row = con.execute(f"SELECT * FROM read_parquet('{self.associations_file.as_posix()}') WHERE relationship_id = '{relationship_id}'").df().to_dict(orient="records")
        con.close()

        if not row:
            return None
        return row[0]

    def get_map_clusters(
        self,
        lat_min: Optional[float] = None,
        lat_max: Optional[float] = None,
        lon_min: Optional[float] = None,
        lon_max: Optional[float] = None,
        sensor: Optional[str] = None,
        limit: int = 300,
    ) -> List[Dict[str, Any]]:
        """Retrieve cluster centroid markers for map rendering within a viewport."""
        files = []
        if not sensor or sensor.upper() == "ALL":
            if self.modis_clusters_file.exists():
                files.append(f"SELECT * FROM read_parquet('{self.modis_clusters_file.as_posix()}')")
            if self.viirs_clusters_file.exists():
                files.append(f"SELECT * FROM read_parquet('{self.viirs_clusters_file.as_posix()}')")
        elif sensor.upper() == "MODIS" and self.modis_clusters_file.exists():
            files.append(f"SELECT * FROM read_parquet('{self.modis_clusters_file.as_posix()}')")
        elif sensor.upper() == "VIIRS" and self.viirs_clusters_file.exists():
            files.append(f"SELECT * FROM read_parquet('{self.viirs_clusters_file.as_posix()}')")

        if not files:
            return []

        union_q = " UNION ALL ".join(files)
        where_clauses = []
        if lat_min is not None and lat_max is not None:
            where_clauses.append(f"centroid_latitude >= {lat_min} AND centroid_latitude <= {lat_max}")
        if lon_min is not None and lon_max is not None:
            where_clauses.append(f"centroid_longitude >= {lon_min} AND centroid_longitude <= {lon_max}")

        where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        con = duckdb.connect()
        data_q = f"""
            SELECT 
                cluster_id, sensor, observation_count, core_count, border_count,
                centroid_latitude, centroid_longitude,
                mean_spatial_spread_km, max_spatial_spread_km,
                sum_frp_mw, mean_frp_mw,
                start_timestamp_utc, end_timestamp_utc, duration_minutes,
                primary_satellite
            FROM ({union_q}) AS u
            {where_str}
            ORDER BY observation_count DESC
            LIMIT {limit}
        """
        rows = con.execute(data_q).df().to_dict(orient="records")
        con.close()

        # Format map objects
        map_items = []
        for r in rows:
            map_items.append({
                "cluster_id": r["cluster_id"],
                "sensor": r["sensor"],
                "latitude": float(r["centroid_latitude"]),
                "longitude": float(r["centroid_longitude"]),
                "observation_count": int(r["observation_count"]),
                "core_count": int(r["core_count"]),
                "border_count": int(r["border_count"]),
                "mean_spatial_spread_km": float(r["mean_spatial_spread_km"]),
                "sum_frp_mw": float(r["sum_frp_mw"]),
                "duration_minutes": float(r["duration_minutes"]),
                "start_timestamp_utc": str(r["start_timestamp_utc"]),
                "end_timestamp_utc": str(r["end_timestamp_utc"]),
                "primary_satellite": str(r["primary_satellite"]),
            })
        return map_items

    def get_map_relationships(
        self,
        lat_min: Optional[float] = None,
        lat_max: Optional[float] = None,
        lon_min: Optional[float] = None,
        lon_max: Optional[float] = None,
        min_score: float = 0.0,
        limit: int = 300,
    ) -> List[Dict[str, Any]]:
        """Retrieve cross-sensor relationship vectors connecting cluster centroids for map display."""
        if not self.associations_file.exists():
            return []

        where_clauses = [f"heuristic_event_score >= {min_score}"]
        if lat_min is not None and lat_max is not None:
            where_clauses.append(f"""
                ((modis_centroid_lat >= {lat_min} AND modis_centroid_lat <= {lat_max})
                 OR (viirs_centroid_lat >= {lat_min} AND viirs_centroid_lat <= {lat_max}))
            """)
        if lon_min is not None and lon_max is not None:
            where_clauses.append(f"""
                ((modis_centroid_lon >= {lon_min} AND modis_centroid_lon <= {lon_max})
                 OR (viirs_centroid_lon >= {lon_min} AND viirs_centroid_lon <= {lon_max}))
            """)

        where_str = f"WHERE {' AND '.join(where_clauses)}"

        con = duckdb.connect()
        data_q = f"""
            SELECT 
                relationship_id, modis_cluster_id, viirs_cluster_id,
                modis_centroid_lat, modis_centroid_lon,
                viirs_centroid_lat, viirs_centroid_lon,
                centroid_distance_km, mean_distance_km, mean_time_diff_minutes,
                supporting_pairs_count, unique_supporting_modis_obs, unique_supporting_viirs_obs,
                heuristic_event_score, multiplicity_type, classification, is_ambiguous
            FROM read_parquet('{self.associations_file.as_posix()}')
            {where_str}
            ORDER BY heuristic_event_score DESC
            LIMIT {limit}
        """
        rows = con.execute(data_q).df().to_dict(orient="records")
        con.close()

        lines = []
        for r in rows:
            lines.append({
                "relationship_id": r["relationship_id"],
                "modis_cluster_id": r["modis_cluster_id"],
                "viirs_cluster_id": r["viirs_cluster_id"],
                "coordinates": [
                    [float(r["modis_centroid_lat"]), float(r["modis_centroid_lon"])],
                    [float(r["viirs_centroid_lat"]), float(r["viirs_centroid_lon"])]
                ],
                "centroid_distance_km": float(r["centroid_distance_km"]),
                "mean_distance_km": float(r["mean_distance_km"]),
                "mean_time_diff_minutes": float(r["mean_time_diff_minutes"]),
                "supporting_pairs_count": int(r["supporting_pairs_count"]),
                "heuristic_event_score": float(r["heuristic_event_score"]),
                "multiplicity_type": str(r["multiplicity_type"]),
                "classification": str(r["classification"]),
                "is_ambiguous": bool(r["is_ambiguous"]),
            })
        return lines


events_manager = EventsManager()
