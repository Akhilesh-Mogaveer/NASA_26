# FireLens — API Design Document

## 1. Introduction

The FireLens backend uses FastAPI to provide processed satellite fire information to the React frontend.

The API separates data processing from visualization and allows the frontend to retrieve observations, comparisons, analytics, and quality reports.

## 2. Technology

- Python
- FastAPI
- Uvicorn
- Pandas
- NumPy
- Pydantic

## 3. Base URL

During local development:

```text
http://localhost:8000
```

## 4. API Endpoints

### 4.1 Root Endpoint

**GET /**

Purpose: Check whether the backend is running.

Example response:

```json
{
  "message": "FireLens API is running",
  "status": "success"
}
```

### 4.2 Health Check

**GET /api/health**

Purpose: Check API health.

Example response:

```json
{
  "status": "healthy"
}
```

### 4.3 Get Fire Observations

**GET /api/fires**

Purpose: Retrieve fire observations.

Optional query parameters:

- sensor
- start_date
- end_date
- min_frp
- limit

Example:

```text
GET /api/fires?sensor=MODIS&limit=100
```

Example response:

```json
{
  "total": 2,
  "observations": [
    {
      "observation_id": "FL-001",
      "latitude": 12.91,
      "longitude": 74.85,
      "instrument": "MODIS",
      "frp": 12.5
    },
    {
      "observation_id": "FL-002",
      "latitude": 13.02,
      "longitude": 75.1,
      "instrument": "VIIRS",
      "frp": 8.4
    }
  ]
}
```

These values are illustrative examples, not real satellite observations.

### 4.4 Sensor Comparison

**GET /api/comparison**

Purpose: Retrieve MODIS and VIIRS comparison information.

Example response:

```json
{
  "modis_count": 120,
  "viirs_count": 180,
  "matched_count": 75,
  "unmatched_modis": 45,
  "unmatched_viirs": 105
}
```

The counts are illustrative.

### 4.5 Activity Analytics

**GET /api/analytics/activity**

Purpose: Retrieve observation counts over time.

Optional parameters:

- start_date
- end_date
- region

Example response:

```json
{
  "daily_activity": [
    {
      "date": "2026-11-12",
      "count": 35
    },
    {
      "date": "2026-11-13",
      "count": 48
    }
  ]
}
```

### 4.6 Anomaly Analysis

**GET /api/analytics/anomalies**

Purpose: Retrieve unusual changes in observed fire activity.

Example response:

```json
{
  "anomalies": [
    {
      "date": "2026-11-13",
      "region": "Example Region",
      "observed_count": 48,
      "historical_mean": 20,
      "z_score": 2.1,
      "status": "unusual_activity"
    }
  ]
}
```

This is an illustrative response. Anomaly thresholds and historical baselines must be defined by the analysis implementation.

### 4.7 Data Quality

**GET /api/quality**

Purpose: Retrieve data validation and quality information.

Example response:

```json
{
  "total_records": 1000,
  "valid_records": 970,
  "invalid_records": 30,
  "duplicate_records": 5,
  "missing_value_records": 20
}
```

These values are illustrative.

## 5. API Error Handling

The API should return appropriate HTTP status codes.

| Status Code | Meaning                      |
| ----------- | ---------------------------- |
| 200         | Successful request           |
| 400         | Invalid request              |
| 404         | Requested resource not found |
| 422         | Validation error             |
| 500         | Internal server error        |

Example error:

```json
{
  "detail": "Invalid date format"
}
```

## 6. API Folder Structure

```text
backend/
│
├── app/
│   ├── main.py
│   │
│   ├── routes/
│   │   ├── fires.py
│   │   ├── comparison.py
│   │   ├── analytics.py
│   │   └── quality.py
│   │
│   ├── services/
│   │   ├── ingestion.py
│   │   ├── validation.py
│   │   ├── normalization.py
│   │   ├── harmonization.py
│   │   └── anomaly.py
│   │
│   └── models/
│       └── schemas.py
│
└── requirements.txt
```

## 7. API Security and Reliability

For the initial prototype:

- Validate incoming query parameters.
- Avoid exposing sensitive credentials.
- Keep NASA API keys in environment variables when required.
- Handle missing datasets gracefully.
- Log processing and API errors.
- Avoid returning unvalidated data as reliable observations.

## 8. API Documentation

FastAPI automatically provides interactive API documentation.

After starting the backend, open:

```text
http://localhost:8000/docs
```

This allows developers to test the endpoints.

## 9. Conclusion

The FireLens API provides a structured connection between satellite data processing and frontend visualization.

It supports modular development and allows additional analysis endpoints to be introduced in future versions.
