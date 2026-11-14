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

## 9. Scientific Considerations

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
