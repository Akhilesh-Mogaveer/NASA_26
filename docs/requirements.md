# FireLens — Project Requirements

**Project Name:** FireLens — A Harmonized Satellite Fire Intelligence Platform

**Challenge:** NASA Space Apps Challenge 2026 — Harmonization of MODIS and VIIRS Hot Spots

**Project Type:** Satellite Data Analytics and Geospatial Intelligence Platform

---

## 1. Problem Statement

NASA's MODIS and VIIRS satellite instruments provide active-fire observations across the globe.

However, these instruments have different spatial resolutions, observation times, sensor characteristics, and detection capabilities.

Comparing their raw observations directly can lead to misleading interpretations and duplicate counting.

FireLens aims to provide a unified platform that processes, compares, and harmonizes MODIS and VIIRS active-fire observations using transparent spatial and temporal analysis.

## 2. Project Objectives

1. Collect authentic MODIS and VIIRS active-fire data from NASA FIRMS.
2. Process and clean satellite observations.
3. Standardize common data fields while preserving sensor-specific information.
4. Develop a spatial-temporal harmonization algorithm.
5. Identify potential duplicate or related observations.
6. Generate daily and monthly fire activity calendars.
7. Visualize satellite fire observations on interactive maps.
8. Compare MODIS and VIIRS detection patterns.
9. Identify unusual fire activity using historical statistical analysis.
10. Provide understandable scientific insights through an interactive web platform.

## 3. Target Users

- Environmental researchers
- Disaster management organizations
- Forest departments
- GIS analysts
- Climate researchers
- Students and data scientists

## 4. Functional Requirements

### FR-01: Satellite Data Collection

- Retrieve MODIS and VIIRS observations from NASA FIRMS.
- Support CSV data imports.
- Preserve original source files and metadata.

### FR-02: Data Processing

- Validate latitude and longitude.
- Process acquisition dates and times.
- Handle missing and invalid values.
- Standardize common fields.
- Preserve original sensor-specific attributes.

### FR-03: Harmonization Engine

- Perform spatial-temporal matching.
- Identify candidate observations from both sensors.
- Calculate geographic distance and time difference.
- Identify ambiguous associations.
- Preserve unmatched observations.
- Allow configurable matching thresholds.

### FR-04: Fire Activity Calendar

- Generate daily fire activity summaries.
- Generate monthly activity summaries.
- Display changes in fire detection activity.
- Allow users to select a date range.

### FR-05: Interactive Fire Map

- Display MODIS and VIIRS observations.
- Provide separate sensor filters.
- Support geographic exploration.
- Display observation details when a user selects a point.

### FR-06: Sensor Comparison

- Compare MODIS and VIIRS observations.
- Display sensor-specific detection counts.
- Show associated and unmatched observations.
- Display matching statistics.

### FR-07: Anomaly Analysis

- Compare current activity with historical baselines.
- Identify statistically unusual activity.
- Display anomaly scores and explanations.
- Show the baseline period and analysis method.

Anomaly detection must not be presented as future fire prediction.

### FR-08: Data Quality

- Display missing and invalid records.
- Show source data coverage.
- Provide processing and validation reports.
- Maintain data provenance.

### FR-09: Data Export

- Allow users to download filtered observations.
- Support CSV exports of summaries and analysis results.

## 5. Non-Functional Requirements

### Performance

- Process manageable regional datasets efficiently.
- Avoid loading unnecessary records into the frontend.

### Reliability

- Handle invalid data and API errors.
- Provide meaningful error messages.

### Usability

- Provide a simple and understandable interface.
- Support desktop and mobile screens.

### Security

- Protect NASA API credentials.
- Use environment variables for secrets.
- Avoid exposing sensitive configuration in frontend code.

### Scientific Transparency

- Preserve original satellite observations.
- Document matching thresholds and processing methods.
- Clearly communicate uncertainty and limitations.
- Ensure derived results can be traced to source observations.

## 6. Proposed Technology Stack

### Frontend

- React
- Vite
- Tailwind CSS
- Leaflet
- Recharts

### Backend

- Python
- FastAPI
- Uvicorn

### Data Science

- Pandas
- NumPy
- SciPy
- Scikit-learn

### Geospatial Processing

- GeoPandas
- Shapely
- PyProj

### Data Storage

- CSV
- Parquet
- PostgreSQL + PostGIS (optional)

### Data Source

- NASA FIRMS
- MODIS active-fire products
- VIIRS active-fire products

### Deployment

- GitHub
- Vercel
- Render

## 7. Project Scope

### Minimum Viable Product (MVP)

- MODIS and VIIRS data ingestion.
- Data validation and normalization.
- Spatial-temporal harmonization.
- Interactive fire map.
- Sensor comparison.
- Daily activity calendar.
- Basic historical anomaly analysis.

### Future Enhancements

- Live satellite data updates.
- Advanced spatial analysis.
- Regional fire activity reports.
- Improved statistical anomaly detection.
- Additional NASA Earth observation datasets.

## 8. Scientific Limitations

- Satellite observations are not complete records of all fires.
- Cloud cover and satellite overpass times affect detections.
- Different sensor resolutions can produce different observations.
- A matched pair does not prove both observations represent the same physical fire.
- Active-fire points do not represent fire boundaries or burned area.
- Anomaly detection does not predict future fire incidents.

## 9. MVP Acceptance Criteria

The project will be considered ready for demonstration when:

1. Authentic MODIS and VIIRS datasets can be imported.
2. Data validation reports are generated.
3. Original observations are preserved.
4. Spatial-temporal associations can be inspected.
5. Daily activity summaries can be generated.
6. Users can explore observations through an interactive map.
7. Sensor comparison is available.
8. Historical anomaly analysis displays its baseline and methodology.
9. The complete application runs successfully.
10. Scientific limitations and data sources are documented.

## 10. Development Strategy

Development will follow a modular approach:

1. Project setup and documentation.
2. NASA data collection.
3. Data ingestion and validation.
4. Data normalization.
5. Harmonization engine.
6. Aggregation and anomaly analysis.
7. Backend API development.
8. Frontend development.
9. Integration and testing.
10. Deployment and demonstration.

---

**Project Vision:**

FireLens aims to transform separate satellite active-fire observations into a transparent, comparable, and accessible source of fire intelligence.
