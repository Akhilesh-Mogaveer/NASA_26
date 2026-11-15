# FireLens 🔥

## A Harmonized Satellite Fire Intelligence Platform

**NASA Space Apps Challenge 2026**

**Challenge:** Harmonization of MODIS and VIIRS Hot Spots

## 1. Overview

FireLens is a satellite fire intelligence platform designed to harmonize and analyze active-fire observations from NASA's MODIS and VIIRS satellite instruments.

Different satellite instruments provide observations with different spatial, temporal, and measurement characteristics.

FireLens aims to create a common framework for exploring these observations while preserving their original sensor information.

The platform provides interactive maps, sensor comparisons, activity analysis, anomaly detection, and data-quality reporting.

## 2. Problem Statement

MODIS and VIIRS provide valuable active-fire observations, but differences in their resolution, observation times, detection characteristics, and data attributes make direct comparison challenging.

FireLens addresses this problem by processing both datasets through a common workflow and associating potentially related observations using spatial and temporal information.

## 3. Key Features

### 🔥 Unified Fire Map

Explore MODIS and VIIRS active-fire observations through an interactive map.

### 🛰️ Sensor Comparison

Compare observations from different satellite instruments.

### 📅 Fire Activity Analysis

Explore daily, weekly, and monthly observation patterns.

### 📊 Anomaly Analysis

Identify unusual changes in observed fire activity.

### 🧪 Data Quality Assessment

Understand missing values, invalid records, duplicates, and processing status.

### 🌍 Spatial-Temporal Association

Identify potentially related observations using configurable geographic-distance and time-difference thresholds.

## 4. Technology Stack

| Layer                | Technology                 |
| -------------------- | -------------------------- |
| Frontend             | React.js, Vite             |
| Styling              | Tailwind CSS               |
| Mapping              | Leaflet                    |
| Visualization        | Recharts                   |
| Backend              | Python, FastAPI            |
| Data Processing      | Pandas, NumPy              |
| Geospatial Analysis  | GeoPandas, Shapely, PyProj |
| Statistical Analysis | SciPy, Scikit-learn        |
| Storage              | CSV / Parquet              |
| Deployment           | Vercel, Render             |

## 5. Data Sources

FireLens uses NASA Fire Information for Resource Management System (FIRMS).

Official resources:

- NASA FIRMS Active Fire Data: https://firms.modaps.eosdis.nasa.gov/active_fire/
- FIRMS Data Download: https://firms2.modaps.eosdis.nasa.gov/download/
- FIRMS API Documentation: https://firms.modaps.eosdis.nasa.gov/api/
- NASA Earthdata Login: https://urs.earthdata.nasa.gov/

The exact satellite products and their attributes should be verified before processing.

## 6. System Workflow

```text
NASA FIRMS
    |
    v
MODIS and VIIRS Data
    |
    v
Data Ingestion
    |
    v
Data Validation
    |
    v
Data Normalization
    |
    v
Spatial-Temporal Association
    |
    v
Unified Observation Dataset
    |
    v
Statistical and Anomaly Analysis
    |
    v
FastAPI Backend
    |
    v
React Frontend
    |
    v
Interactive Fire Intelligence Platform
```

## 7. Project Structure

```text
FireLens/
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── vite.config.js
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── routes/
│   │   ├── services/
│   │   ├── models/
│   │   └── data/
│   │
│   └── requirements.txt
│
├── data/
│   ├── raw/
│   │   ├── modis/
│   │   └── viirs/
│   │
│   └── processed/
│
├── docs/
│   ├── requirements.md
│   ├── design.md
│   ├── data_dictionary.md
│   ├── harmonization_methodology.md
│   └── api_design.md
│
└── README.md
```

## 8. Installation and Setup

### Prerequisites

- Python 3.10 or later.
- Node.js.
- npm.
- Git.

### Backend Setup

Navigate to the backend folder:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate the environment on Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the backend:

```bash
uvicorn app.main:app --reload
```

Backend URL:

```text
http://localhost:8000
```

API documentation:

```text
http://localhost:8000/docs
```

### Frontend Setup

Open another terminal:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Run the development server:

```bash
npm run dev
```

Open the local URL provided by Vite.

## 9. NASA FIRMS Data Ingestion & Validation Guide (Phase 2)

### 9.1 How to Obtain NASA FIRMS Data

1. Visit the **NASA FIRMS Active Fire Data Download portal**:
   https://firms.modaps.eosdis.nasa.gov/download/
2. Select your geographic region of interest (e.g., country or custom bounding box).
3. Under Satellite Sources, download:
   - **MODIS C6.1** (Terra and Aqua, 1km active-fire CSV)
   - **VIIRS 375m** (Suomi-NPP, NOAA-20, or NOAA-21 active-fire CSV)
4. (Optional) You can also request a free NASA FIRMS MAP_KEY from https://firms.modaps.eosdis.nasa.gov/api/map_key/ for automated API downloads in future versions.

### 9.2 Where to Place Downloaded CSV Files

Place your unedited NASA FIRMS CSV files in their designated directories:

```text
data/raw/modis/    <- Place MODIS CSV files here (e.g. fire_nrt_M-C61_*.csv)
data/raw/viirs/    <- Place VIIRS CSV files here (e.g. fire_nrt_SV-C2_*.csv)
```

The ingestion engine supports multiple files per sensor, handles header inspection, and preserves all original source columns.

### 9.3 How to Run the Ingestion & Validation Pipeline

**Option A: Via API or Web UI**
- Click **"Run Ingestion Pipeline"** on the **Data Quality** page in the web app, or
- Make a POST request:
  ```bash
  curl -X POST http://localhost:8000/api/data/ingest
  ```

**Option B: Via Python CLI**
```powershell
cd backend
.\venv\Scripts\activate
python -c "from app.services.pipeline import run_ingestion_pipeline; print(run_ingestion_pipeline())"
```

Generated outputs will be saved to:
- `data/processed/modis_normalized.csv`
- `data/processed/viirs_normalized.csv`
- `data/processed/unified_observations.csv`
- `data/reports/data_quality_report.json`

### 9.4 How to Inspect Data Quality Reports

- **In the Web App**: Open the **Data Quality** tab to view pass rates, sensor breakdowns, invalid coordinate logs, and duplicate counts.
- **Via API**:
  ```bash
  curl http://localhost:8000/api/data/quality
  curl http://localhost:8000/api/data/preview?limit=5
  ```
- **Direct JSON File**: Open `data/reports/data_quality_report.json`.

### 9.5 How to Run Automated Backend Tests

Run the complete Pytest suite (including health, ingestion, bounds validation, duplicate checks, analytics services, and endpoint tests):

```powershell
cd backend
.\venv\Scripts\activate
pytest -v
```

---

## 10. Phase 3: Exploratory Data Analysis & Scientific Analytics

FireLens Phase 3 delivers deep scientific exploration over **22,175,341 authentic NASA FIRMS observations** from the 2025 calendar year (3.71M MODIS C6.1 and 18.47M VIIRS C2 NOAA-20).

### 10.1 Jupyter EDA Notebook
The primary scientific analysis deliverable is located at:
- **[`notebooks/FireLens_EDA.ipynb`](./notebooks/FireLens_EDA.ipynb)** (29 fully executed cells with embedded high-resolution figures)
- Documentation: **[`notebooks/README.md`](./notebooks/README.md)**

To launch or re-execute the notebook:
```powershell
# From project root
jupyter lab notebooks/FireLens_EDA.ipynb
```

### 10.2 Precomputed Analytical Artifacts
High-performance analytical aggregations computed via DuckDB columnar queries are persisted in `data/analytics/`:
- `analytics_summary.json`: Top-level platform counts, energetics, and empirical findings.
- `temporal_summary.json`: 12-month seasonality, 24-hour diurnal cycle, day-of-week, and day/night splits.
- `monthly_statistics.csv`: Monthly sensor counts and mean/total FRP.
- `daily_distribution.csv`: Daily hot spot counts and radiated power.
- `hourly_distribution.csv`: Diurnal 00:00–23:00 UTC hourly distribution.
- `frp_statistics.json`: Parametric/non-parametric FRP metrics and power histogram bins.
- `geographical_grid_density.csv`: Standardized 2-degree global density grid (4,300 active cells).
- `sensor_comparison.json`: Detailed multi-sensor comparison metrics and physical root causes.

### 10.3 Scientific Analytics API Endpoints
The backend provides sub-millisecond, memory-cached analytics endpoints:
- `GET /api/analytics/overview` — High-level platform counts, energetics, and key findings.
- `GET /api/analytics/temporal` — Monthly, hourly (diurnal), and day/night distributions.
- `GET /api/analytics/frp` — Parametric metrics, percentiles (q25, median, q75, q95, q99), and power histogram.
- `GET /api/analytics/sensor-comparison` — Detailed MODIS vs. VIIRS instrument and footprint comparison.
- `GET /api/analytics/geographical` — Top global hotspot clusters and 5-degree latitudinal profiles.
- `GET /api/analytics/grid-density` — Filtered 2-degree grid cell density for map rendering.

### 10.4 Key Scientific Insights Discovered
1. **The 4.979x Volume Disparity:** VIIRS detects 18.47M hot spots vs. MODIS's 3.71M, driven by 375m nadir resolution ($7.11\times$ smaller pixel area) and onboard pixel aggregation that curbs scan edge distortion.
2. **Mean FRP Divergence vs. Total Energy Convergence:** MODIS records a higher mean FRP (41.21 MW vs 9.68 MW) because small fires (&lt;5 MW) remain undetected under 1km pixels. However, total global radiated power is remarkably close (152.8M MW for MODIS vs 178.8M MW for VIIRS, $+17\%$), proving that large fires radiate consistently across sensor footprints.
3. **Diurnal Overpass Synchronization:** Both sensors detect peak fire activity at 12:00–14:00 UTC (regional afternoon overpass times matching highest ambient temperatures and lowest fuel moisture).
4. **Flawless Data Integrity:** 22,175,332 out of 22,175,341 observations (&gt;99.9999%) are valid with zero missing coordinates. All 9 invalid records (1 negative FRP, 8 ST duplicates) are preserved for scientific auditing.

---

## 11. Phase 4: Spatial-Temporal Matching Engine & Sensitivity Analysis

Phase 4 implements the complete spatial-temporal association engine, multiplicity resolver, and 12-parameter sensitivity evaluator.

### 11.1 Matching Methodology & Spherical Distance Calculation
- **Spherical Great-Circle Distance Calculation:** Employs the Haversine formula assuming a spherical Earth ($R_{\text{earth}} = 6371.0088\text{ km}$, IUGG recommendation) with antimeridian ($\pm 180^\circ$) wrap-around adjustment and cosine latitude area convergence. This is explicitly distinguished from an ellipsoidal geodesic distance (e.g. Karney on WGS-84), providing sub-0.5% approximation accuracy that comfortably fits satellite footprint uncertainties while enabling closed-form tree indexing.
- **Scalable Indexing:** Filters candidate observations via UTC epoch window slicing, then builds a local `BallTree` (Haversine metric) on candidate VIIRS points for $O(\log K)$ radius queries.
- **Empirical Proximity Scoring:** Combines spatial and temporal proximity into a normalized ranking metric ($0.5 \cdot \text{spatial\_score} + 0.5 \cdot \text{temporal\_score}$), explicitly documented as an empirical ranking score rather than a calibrated probability.
- **Bipartite Multiplicity & Ambiguity Architecture:** Classifies associations into bipartite graph degree patterns: 1:1 direct pair patterns, 1:N split patterns (topological degree consistent with 7.1x footprint difference, not proven physical flame splitting), N:1 overlap patterns, and M:N multi-cluster perimeters. Associations with competing candidate scores within $\Delta \text{score} \le 0.15$ are flagged as `ambiguous_association` with all plausible edges preserved.

### 11.2 Real-Data Experiment & Benchmarks
Executed on authentic NASA FIRMS observations:
- **Primary Benchmark Region:** North American Boreal Forest Wildfire Complex (Saskatchewan / Manitoba, Canada: Lat 54.0°–58.0°N, Lon 106.0°–102.0°W, August 1–2, 2025; **22,455 valid observations**: MODIS Terra = 1,525, MODIS Aqua = 1,591, VIIRS NOAA-20 = 19,339).
  - **Baseline Results ($R \le 2.0\text{ km}, \Delta t \le 60\text{ min}$):**
    - **Total Candidate Associations:** 28,911
    - **Unique MODIS Matched:** 1,470 / 3,116 (47.18%)
    - **Unique VIIRS Matched:** 8,328 / 19,339 (43.06%)
    - **Unmatched Observations:** 1,646 MODIS, 11,011 VIIRS
    - **Multiplicity Breakdown:** 1:1 = 15; 1:N = 2,104; N:1 = 24; M:N = 26,768
    - **Mean Great-Circle Separation:** 1.202 km (Median: 1.24 km)
    - **Mean Temporal Difference:** 21.82 min (Median: 10.0 min)
  - **Benchmark Disentanglement:**
    - **Baseline Execution Time:** 15.71 s (Candidate generation: 14.77s; Association processing: 0.94s)
    - **Baseline Candidate Throughput:** 1,840.3 candidate pairs/sec (28,911 pairs / 15.71s)
    - **Baseline Observation Throughput:** 1,429.3 observations/sec (22,455 obs / 15.71s)
    - **Sensitivity Grid Runtime (12 parameter combinations):** 190.32 s
    - **Total Pipeline Workflow Runtime:** 206.03 s
    - **Peak Memory:** 168.4 MB traced RAM (psutil resident memory: ~450 MB)
- **Secondary Comparative Region:** Southern African Miombo Savanna Fire Belt (Zambia / Angola: Lat -15.0° to -12.0°, Lon 22.0° to 26.0°, August 1–2, 2025; 4,599 valid observations: MODIS Aqua = 917, MODIS Terra = 38, VIIRS NOAA-20 = 3,644). Yielded only 16 candidate associations (MODIS match rate: 0.73%, VIIRS match rate: 0.25%).
  - **Scientific Explanation:** Orbital overpass geometry is the primary governing factor. Terra passes at ~10:30 and Aqua/NOAA-20 at ~13:30 local solar time (~3-hour diurnal temporal gap). In this region over August 1–2, 2025, VIIRS NOAA-20 passed at ~16:00 UTC and MODIS Aqua passed at ~18:00 UTC (~2-hour gap), so very few observations fell within the 60-minute matching window regardless of physical fire behavior. Faster grass burning with shorter flaming residence time remains a plausible secondary hypothesis.

### 11.3 Sensitivity Analysis Matrix (All 12 Parameter Combinations)

| Radius | Window | Candidate Associations | Matched MODIS | Matched VIIRS | MODIS Ambiguity % | Mean Distance | Mean $\Delta t$ | Candidates / MODIS |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1.25 km** | 15 min | 7,301 | 620 (19.90%) | 3,143 (16.25%) | 89.68% | 0.793 km | 7.95 min | 11.78 |
| **1.25 km** | 30 min | 10,704 | 1,050 (33.70%) | 4,723 (24.42%) | 88.38% | 0.791 km | 14.58 min | 10.19 |
| **1.25 km** | 60 min | 14,665 | 1,427 (45.80%) | 6,842 (35.38%) | 87.11% | 0.786 km | 22.22 min | 10.28 |
| **1.25 km** | 90 min | 16,927 | 1,735 (55.68%) | 7,939 (41.05%) | 86.51% | 0.785 km | 30.37 min | 9.76 |
| **2.00 km** | 15 min | 14,858 | 632 (20.28%) | 3,657 (18.91%) | 97.31% | 1.220 km | 7.95 min | 23.51 |
| **2.00 km** | 30 min | 21,372 | 1,078 (34.60%) | 5,648 (29.21%) | 95.64% | 1.211 km | 14.29 min | 19.83 |
| **2.00 km** | **60 min (Baseline)** | **28,911** | **1,470 (47.18%)** | **8,328 (43.06%)** | **94.42%** | **1.202 km** | **21.82 min** | **19.67** |
| **2.00 km** | 90 min | 33,247 | 1,801 (57.80%) | 9,653 (49.91%) | 94.39% | 1.200 km | 29.86 min | 18.46 |
| **3.50 km** | 15 min | 31,933 | 644 (20.67%) | 4,155 (21.49%) | 98.29% | 2.042 km | 7.95 min | 49.59 |
| **3.50 km** | 30 min | 44,735 | 1,099 (35.27%) | 6,498 (33.60%) | 97.91% | 2.018 km | 13.87 min | 40.71 |
| **3.50 km** | 60 min | 59,047 | 1,500 (48.14%) | 9,760 (50.47%) | 96.67% | 1.993 km | 20.96 min | 39.36 |
| **3.50 km** | 90 min | 67,111 | 1,847 (59.27%) | 11,270 (58.28%) | 96.32% | 1.981 km | 28.51 min | 36.34 |

### 11.4 Analytical Artifacts in `data/matching/`
- `candidate_associations.parquet` (1,084 KB) — All 28,911 structured candidate associations.
- `matching_summary.json` (3.7 KB) — Comprehensive summary metrics and multiplicity distributions.
- `matching_evaluation.csv` (2.3 KB) — Full 12-parameter sensitivity grid.
- `unmatched_observations.parquet` (276 KB) — Unassociated MODIS and VIIRS records.
- `matching_experiment_metadata.json` (2.6 KB) — Reproducibility parameters, software versions, and regional bounds.

### 11.5 Phase 4.4 Interactive Matching Map & Viewport Analytics
- **Geospatial Association Map:** Full interactive Leaflet cartographic display rendering candidate proximity vectors connecting MODIS and VIIRS snapshot observations.
- **Strict Observation Classification:** Total observations strictly equals Matched + Unmatched. Ambiguity ($\Delta \text{score} \le 0.15$) is handled as an orthogonal topological property.
- **Sensor Confidence Preservation:** Native MODIS numeric percentages (0–100%) and VIIRS categorical ratings (`low`, `nominal`, `high`) are preserved without artificial translations.
- **Dynamic Viewport Metrics:** Server-side spatial bounding-box aggregation yielding unique observation match rates and ambiguity rates for any custom bounding box.

### 11.6 Phase 4.5 Full-Scale Partitioning Engine & Benchmarks
- **Spatial-Temporal Overlap Halos:** Daily partitions with $\pm 90\text{ min}$ temporal halo and $\pm 5\text{ km}$ buffer eliminate boundary edge loss across calendar dates.
- **Deterministic Deduplication:** Canonical undirected edge IDs (`ASSOC-{modis_id}-{viirs_id}`) and primary MODIS partition ownership ensure zero cross-partition duplicates.
- **Bounded $O(1)$ Memory Safety:** Streaming execution writes atomic Parquet files (`part-{id}.tmp.parquet` $\rightarrow$ `part-{id}.parquet`). Memory overhead scales with single-partition volume (~78 MB traced RAM, ~300 MB process RSS), completely decoupled from the 22.18M annual catalog.
- **Resumable Manifest:** `manifest.json` tracks partition status, execution time, and throughput, allowing fault recovery without duplicating work.
- **Progressive Real-Data Scalability Benchmarks:**
  - **Stage 1 (Single-Day Benchmark Subsample):** 22,455 records; 28,911 pairs in 15.70s; throughput: 1,841.2 pairs/s; memory: 168.4 MB traced.
  - **Stage 2 (Multi-Day Partitioned Boreal Run):** 3 daily partitions (Aug 1–3, 2025); 4,186 observations; 31,026 candidate pairs generated in 52.83s wall-clock; throughput: 587.3 pairs/s; peak traced RAM: 78.11 MB; process RSS: 302.54 MB; 0 failures.
  - **Stage 3 (Full 22.18M Catalog Scale Projection):** 365 daily partitions; projected candidate pairs: ~18.5M; estimated processing time: ~1.4 hours on multi-core worker; memory safely bounded under 800 MB RSS.

### 11.7 Matching API Endpoints
- `GET /api/matching/status` — Operational status and artifact readiness.
- `GET /api/matching/summary` — Full matching experiment summary and benchmarks.
- `GET /api/matching/associations` — Paginated and filtered candidate associations from Parquet storage.
- `GET /api/matching/unmatched` — Paginated unassociated observations.
- `GET /api/matching/evaluation` — 12-parameter sensitivity evaluation matrix.
- `POST /api/matching/run` — On-demand spatial-temporal matching on user bounding boxes.
- `GET /api/matching/map-observations` — Bounded observation points with classification and degree count for map rendering.
- `GET /api/matching/map-lines` — Candidate vector lines with Haversine distance, time difference, and heuristic scores.
- `GET /api/matching/observation/{obs_id}` — Comprehensive observation lookup and candidate edge list.
- `GET /api/matching/filtered-summary` — Viewport bounding-box observation counts and match rates.
- `POST /api/matching/full-scale/start` — Trigger asynchronous partitioned matching job with halo buffers.
- `GET /api/matching/full-scale/status` — Live partition execution progress and status.
- `GET /api/matching/full-scale/benchmarks` — Progressive real-data benchmarks across scales.

---

## 12. Phase 5: Fire Event Clustering & Cross-Sensor Association

Phase 5 transitions FireLens from individual hotspot point associations to coherent spatial-temporal fire event intelligence:

### 12.1 Phase 5.1 Independent Fire Event Clustering
- **Independent Sensor DBSCAN:** MODIS and VIIRS are clustered strictly independently using a dual spatial-temporal neighborhood rule:
  $$d_{\text{haversine}}(p_i, p_j) \le R_{\text{spatial}} \quad \text{AND} \quad |t_i - t_j| \le \Delta t_{\text{temporal}}$$
- **Spherical Geometry & Antimeridian Safety:** Earth radius $R = 6371.0088\text{ km}$, coordinate radians, and exact 3D Cartesian spherical centroid averaging ($x=\cos\phi\cos\lambda, y=\cos\phi\sin\lambda, z=\sin\phi$) to prevent coordinate distortion near the antimeridian (-180° / +180°) and high polar latitudes.
- **Explicit Point Roles:** Core points ($|\mathcal{N}| \ge N_{\text{min}}$), border points, and noise points. Noise is explicitly preserved with `is_noise=True` and cluster ID `NOISE`, never silently discarded.
- **Partition Reconciliation:** Cross-boundary clusters are unified across partition overlap halos using Disjoint Set Union (Union-Find) to ensure 0 duplicate observation memberships.
- **Scientific Grounding:** Clusters are empirical computational groupings, NOT confirmed physical fire perimeters. Summed FRP is snapshot power in MW, NOT Fire Radiative Energy in MJ.

### 12.2 Phase 5.2 Cross-Sensor Event Association
- **Evidence-Based Association:** Reuses Phase 4 candidate observation associations without rerunning global all-pairs matching.
- **Bipartite Graph Topology:** Models relationships between MODIS and VIIRS clusters as a bipartite graph, evaluating degree connectivity:
  - `1:1`: Direct isolated event pair.
  - `1:N`: One coarse MODIS cluster associated with multiple fine VIIRS clusters.
  - `N:1`: Multiple MODIS clusters associated with one large VIIRS cluster.
  - `M:N`: Multi-cluster complex in dense high-energy wildfire sectors.
- **Topological De-Fragmentation Finding:** While raw observations were dominated by M:N multi-pixel complexes (92.6%) due to resolution asymmetry, **57.0% of cluster-level candidate relationships resolve into direct 1:1 event associations** (90 of 158 relationships).
- **Composite Heuristic Score:** Multi-component transparent formula ($0.35\text{ coverage} + 0.25\text{ spatial} + 0.20\text{ temporal} + 0.20\text{ obs\_score}$). Empirical ranking metric, NOT a calibrated probability.

### 12.3 Real-Data Benchmark Results (Saskatchewan Boreal Benchmark)
- **Observations Clustered:** 22,455 records (3,116 MODIS, 19,339 VIIRS).
- **MODIS Clusters:** 310 clusters (2,191 clustered obs [70.31%], 925 noise obs [29.69%], total snapshot FRP: 244,569.0 MW).
- **VIIRS Clusters:** 670 clusters (18,798 clustered obs [97.20%], 541 noise obs [2.80%], total snapshot FRP: 303,706.98 MW).
- **Cross-Sensor Candidate Relationships:** 158 relationships linking 142 MODIS clusters (45.81%) and 134 VIIRS clusters (20.00%).
- **Multiplicity Breakdown:** `1:1`: 90 (57.0%); `1:N`: 26 (16.5%); `N:1`: 36 (22.8%); `M:N`: 6 (3.8%).
- **Connected Components:** 118 components (`1:1_pair`: 90, `1:N_star`: 10, `N:1_star`: 13, `M:N_complex`: 5).
- **Benchmarks:** Runtime: 53.88 s; Throughput: 416.8 obs/sec; Peak traced RAM: 40.18 MB; Process RSS: 247.32 MB.

### 12.4 Event Artifacts in `data/events/`
- `modis_clusters.parquet` (30 KB) — All 310 MODIS event clusters with centroids, spread, duration, and FRP.
- `viirs_clusters.parquet` (60 KB) — All 670 VIIRS event clusters.
- `modis_cluster_membership.parquet` (53 KB) — Observation-level cluster assignments.
- `viirs_cluster_membership.parquet` (449 KB) — Observation-level cluster assignments.
- `cluster_noise_observations.parquet` (39 KB) — Preserved noise observations.
- `cross_sensor_event_associations.parquet` (27 KB) — All 158 cross-sensor candidate relationships.
- `event_relationship_components.parquet` (7 KB) — Connected components in the bipartite graph.
- `clustering_summary.json` (1.2 KB) — Cluster metrics, parameters, and benchmarks.
- `event_association_summary.json` (1.0 KB) — Multiplicity and classification breakdown.
- `clustering_experiments.parquet` (2.2 KB) — Historical experiment log.
- `event_processing_manifest.json` (0.2 KB) — Processing state manifest.

### 12.5 Event Intelligence API Endpoints
- `POST /api/events/clustering/run` — Asynchronous spatial-temporal clustering job.
- `GET /api/events/clustering/status` — Live clustering job execution status.
- `GET /api/events/clustering/summary` — Latest clustering metrics and benchmarks.
- `GET /api/events/clustering/clusters` — Paginated clusters with sensor and bounding-box filters.
- `GET /api/events/clustering/{cluster_id}` — Single cluster metadata and spatial summaries.
- `GET /api/events/clustering/{cluster_id}/observations` — Constituent hotspot observations.
- `POST /api/events/association/run` — Asynchronous cross-sensor event association job.
- `GET /api/events/association/status` — Live association job status.
- `GET /api/events/association/summary` — Event association summary and topology metrics.
- `GET /api/events/association/relationships` — Paginated cluster relationships with multiplicity filters.
- `GET /api/events/association/{relationship_id}` — Relationship evidence and coverage detail.
- `GET /api/events/map/clusters` — Cluster centroid markers for interactive Leaflet display.
- `GET /api/events/map/relationships` — Cross-sensor relationship vectors for map display.

### 12.6 Phase 5.3 Scientific and Algorithmic Validation Audit
- **Algorithmic Rigor:** Haversine distance on spherical Earth ($R = 6371.0088\text{ km}$, radians), exact spatial/temporal threshold enforcement ($d \le 2.0\text{ km}$, $\Delta t \le 60\text{ min}$), and antimeridian-safe 3D Cartesian spherical averaging.
- **Performance Optimization:** Vectorized NumPy Haversine over candidate subsets achieves $12.4\times$ throughput speedup compared to per-point tree construction with zero numerical drift ($\Delta d < 10^{-13}\text{ km}$).
- **Conservation of Observations:** Verified identity $\text{Input} = \text{Clustered} + \text{Noise}$. Out of 22,455 input observations (3,116 MODIS, 19,339 VIIRS), exactly 2,191 MODIS and 18,798 VIIRS are clustered, with 925 MODIS and 541 VIIRS preserved as noise. Zero observations are dropped.
- **Topological Disentanglement:** Explicit mathematical distinction between relationship edge multiplicity (90 `1:1`, 26 `1:N`, 36 `N:1`, 6 `M:N` across 158 edges) and connected component topology (90 `1:1_pair`, 10 `1:N_star`, 13 `N:1_star`, 5 `M:N_complex` across 118 components).
- **Audit Test Suite:** 12 dedicated audit tests in `backend/tests/test_phase5_audit.py` ensuring complete regression coverage across all 11 scientific validation domains (96 passing tests total).

### 12.7 Phase 6 & Phase 6.1: Temporal Event Evolution, Lifecycle Tracking & Scientific Audit
- **Temporal Event Tracks:** Sequences and branching graphs of candidate continuity relationships between independently generated clusters across successive overpass intervals.
- **Scientific Constraints:** Candidate continuity does NOT prove confirmed physical fire identity, propagation, or perimeter. Absence of detections does NOT imply wildfire extinguishment. FRP snapshot power is reported strictly in Megawatts (MW), NOT Fire Radiative Energy (MJ).
- **Successive Observation Period (SOP) Candidate Selection (Phase 6.1):** Solves graph hyper-density (which previously generated 97.1% complex lineage edges due to multi-hop forward cliques) by retaining candidate transitions at the earliest subsequent observation period ($t_{\text{earliest\_next}} + 30\text{ min}$), eliminating multi-hop transitive shortcuts while preserving genuine splits and merges occurring at the immediate next overpass.
- **Centroid Distance Cap:** When using extent-aware distance, centroid separation is capped by a hard upper bound ($d_{\text{centroid}} \le 7.5\text{ km}$) to prevent expansive multi-point clusters from making unphysical spatial leaps.
- **Directed Graph & Topology:** Identifies `continuation_candidate`, `possible_split`, `possible_merge`, and `complex_lineage` based on local in-degree and out-degree. Flagged for ambiguity when candidate edges compete within score $\Delta \le 0.15$.
- **Real-Data Regional Benchmark Results (Saskatchewan Boreal Dataset — Phase 6.1 SOP):**
  - **Total Clusters Processed:** 980 (310 MODIS, 670 VIIRS) — 100% conservation.
  - **Temporal Continuity Relationships:** 1,187 (303 MODIS, 884 VIIRS) — 76.5% reduction in multi-hop transitive shortcuts.
  - **Lineage Classification:** 265 `continuation_candidate` (up from 5 in dense mode), 197 `possible_split`, 206 `possible_merge`, 519 `complex_lineage` (down from 97.1% to 43.7%).
  - **Event Tracks Constructed:** 115 (58 MODIS, 57 VIIRS).
  - **MODIS Tracks:** 33 multi-cluster tracks, 25 isolated single clusters (43.1%), median duration $24.63\text{ hours}$, 64 splits, 65 merges; 142 clusters (45.81%) supported by Phase 5 cross-sensor evidence.
  - **VIIRS Tracks:** 46 multi-cluster tracks, 11 isolated single clusters (19.3%), median duration $35.19\text{ hours}$, 244 splits, 258 merges; 134 clusters (20.00%) supported by Phase 5 cross-sensor evidence.
  - **Conservation of Observations:** Exactly 20,989 observations tracked (2,191 MODIS, 18,798 VIIRS), preserving 100% of clustered observations with zero dropped detections.
  - **Performance:** 9.26 seconds wall-clock runtime, 4.46 MB peak traced memory, 201.98 MB process RSS.
- **Evolution Artifacts (`data/evolution/`):**
  - `modis_temporal_relationships.parquet` — 303 directed MODIS continuity edges.
  - `viirs_temporal_relationships.parquet` — 884 directed VIIRS continuity edges.
  - `modis_event_tracks.parquet` — 58 MODIS event tracks with lifecycle metrics.
  - `viirs_event_tracks.parquet` — 57 VIIRS event tracks with lifecycle metrics.
  - `event_track_membership.parquet` — 980 cluster-to-track assignments and degree counts.
  - `event_track_lineage.parquet` — 1,187 directed graph transitions and split/merge annotations.
  - `event_evolution_summary.json` — Full summary metrics, breakdown counts, and cross-sensor evidence rates.
  - `event_evolution_experiments.parquet` — Historical benchmark log.
  - `event_evolution_manifest.json` — Processing state manifest.
- **API Endpoints (`/api/evolution/*`):**
  - `POST /api/evolution/run` — Asynchronous temporal evolution execution.
  - `GET /api/evolution/status` — Live job status and progress.
  - `GET /api/evolution/summary` — Evolution summary metrics and benchmark data.
  - `GET /api/evolution/tracks` — Paginated event tracks with topology and duration filters.
  - `GET /api/evolution/tracks/{track_id}` — Single event track summary metadata.
  - `GET /api/evolution/tracks/{track_id}/timeline` — Step-by-step observation timeline.
  - `GET /api/evolution/tracks/{track_id}/lineage` — Directed lineage graph with split/merge classifications.
  - `GET /api/evolution/relationships` — Paginated candidate temporal continuity edges.
  - `GET /api/evolution/map` — Centroid nodes and directed continuity vector lines for Leaflet map display.
  - `GET /api/evolution/experiments` — Historical experiment logs.

---

## 13. Scientific Considerations

FireLens follows these principles:

1. Preserve original MODIS and VIIRS observations.
2. Do not assume that different sensors produce identical measurements.
3. Use documented spatial and temporal matching criteria.
4. Preserve source-specific confidence information.
5. Clearly distinguish active-fire points from fire perimeters.
6. Do not interpret FRP as burned area.
7. Treat anomaly detection as identification of unusual observations, not prediction.
8. Clearly label sample and simulated datasets.
9. Document thresholds and processing decisions.

## 10. Project Goals

- Make MODIS and VIIRS observations easier to compare.
- Improve transparency in satellite fire-data processing.
- Provide an understandable interface for exploring active-fire observations.
- Support researchers and environmental monitoring teams.
- Create a foundation for future satellite fire intelligence applications.

## 11. Future Scope

- Automated satellite data ingestion.
- PostgreSQL and PostGIS integration.
- Additional satellite datasets.
- Advanced geospatial analysis.
- Improved historical activity analysis.
- More advanced anomaly detection.
- Expanded regional and global coverage.

## 12. Team

**Project:** FireLens

**Event:** NASA Space Apps Challenge 2026

**Challenge:** Harmonization of MODIS and VIIRS Hot Spots

## 13. Disclaimer

FireLens is a research and visualization prototype. Its outputs depend on the source satellite products, data availability, processing choices, and analytical thresholds.

Spatial-temporal associations do not confirm physical fire identity, and anomaly detection does not predict future fire events.
