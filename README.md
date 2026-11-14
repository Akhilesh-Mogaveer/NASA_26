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

## 11. Scientific Considerations

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
