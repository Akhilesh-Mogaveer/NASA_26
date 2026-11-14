# FireLens — Data Dictionary

## 1. Introduction

This document describes the data fields used by FireLens to process and harmonize MODIS and VIIRS active-fire observations.

The platform maintains two types of information:

1. Original source attributes.
2. Common normalized attributes.

The original attributes must be preserved to maintain data provenance and support sensor-specific analysis.

## 2. Data Sources

### MODIS

MODIS stands for Moderate Resolution Imaging Spectroradiometer.

It provides active-fire observations from satellite instruments aboard Terra and Aqua.

### VIIRS

VIIRS stands for Visible Infrared Imaging Radiometer Suite.

It provides active-fire observations from compatible satellite platforms.

The exact attributes available depend on the selected FIRMS product and download format.

## 3. Common Data Fields

| Field             | Data Type       | Description                              |
| ----------------- | --------------- | ---------------------------------------- |
| observation_id    | String          | Unique identifier created by FireLens    |
| latitude          | Float           | Geographic latitude                      |
| longitude         | Float           | Geographic longitude                     |
| acquisition_date  | Date            | Observation date                         |
| acquisition_time  | String          | Observation time                         |
| satellite         | String          | Satellite identifier                     |
| instrument        | String          | MODIS or VIIRS                           |
| confidence        | String / Number | Source-specific confidence information   |
| frp               | Float           | Fire Radiative Power, when available     |
| brightness        | Float           | Brightness measurement, when available   |
| scan              | Float           | Scan measurement, when available         |
| track             | Float           | Track measurement, when available        |
| daynight          | String          | Day or night observation, when available |
| source_file       | String          | Original dataset filename                |
| processing_status | String          | Processing status                        |

## 4. Important Source Attributes

The following fields may be present in FIRMS products. Their names and definitions must be checked against the exact product documentation being used.

### Latitude

Represents the latitude of the detected active-fire location.

### Longitude

Represents the longitude of the detected active-fire location.

### Brightness Temperature

Represents the satellite-measured brightness temperature for a specified channel.

It is not automatically the same as the actual surface temperature of a fire.

### Fire Radiative Power (FRP)

Represents the estimated radiant energy released by the detected fire.

FRP is useful for understanding fire intensity at the time of observation.

FRP is not the same as burned area.

### Confidence

Represents the confidence information supplied by the source product.

Confidence definitions and scales may differ between products.

FireLens must not assume that MODIS and VIIRS confidence values are directly comparable without checking their documentation.

### Scan and Track

These fields describe the dimensions of the satellite observation footprint in the source product.

They may be useful when interpreting spatial uncertainty.

### Day/Night

Indicates whether the observation occurred during daytime or nighttime, when provided by the source.

## 5. Harmonized Data Structure

FireLens uses a common structure for analysis.

Example:

```json
{
  "observation_id": "FL-000001",
  "latitude": 12.91,
  "longitude": 74.85,
  "acquisition_date": "2026-11-14",
  "acquisition_time": "0830",
  "satellite": "Terra",
  "instrument": "MODIS",
  "frp": 12.5,
  "confidence": "source_value",
  "source_file": "modis_sample.csv",
  "processing_status": "valid"
}
```

This is an illustrative normalized record, not a real NASA observation.

## 6. Harmonization Relationship Fields

The following fields are created by FireLens during spatial-temporal association.

| Field                  | Data Type | Description                                                |
| ---------------------- | --------- | ---------------------------------------------------------- |
| match_group_id         | String    | Identifier for a group of potentially related observations |
| matched_observation_id | String    | Identifier of a related observation                        |
| distance_km            | Float     | Geographic distance between observations                   |
| time_difference_min    | Float     | Difference in observation time                             |
| match_status           | String    | Matched, unmatched, or uncertain                           |
| matching_method        | String    | Method used for association                                |

These fields describe analytical relationships, not confirmed physical fire identities.

## 7. Data Quality Fields

| Field              | Data Type | Description                               |
| ------------------ | --------- | ----------------------------------------- |
| is_valid           | Boolean   | Indicates whether basic validation passed |
| missing_fields     | Array     | List of missing required fields           |
| is_duplicate       | Boolean   | Indicates a suspected duplicate           |
| validation_message | String    | Validation explanation                    |
| processed_at       | Datetime  | Processing timestamp                      |

## 8. Data Processing Rules

1. Preserve the original source records.
2. Validate latitude and longitude ranges.
3. Check timestamp formats.
4. Identify missing required values.
5. Identify potential duplicates.
6. Preserve sensor-specific fields.
7. Convert compatible fields into a common structure.
8. Record the source dataset and processing method.
9. Avoid treating missing values as zero.
10. Avoid assuming that measurements from different sensors are identical.

## 9. Example Dataset Organization

```text
data/
│
├── raw/
│   ├── modis/
│   │   └── modis_sample.csv
│   │
│   └── viirs/
│       └── viirs_sample.csv
│
├── processed/
│   ├── modis_normalized.csv
│   ├── viirs_normalized.csv
│   ├── unified_observations.csv
│   └── matched_observations.csv
│
└── reports/
    └── data_quality_report.json
```

## 10. Important Note

The exact field names, units, confidence definitions, and availability must be verified using the documentation for the selected NASA FIRMS products.

The data dictionary must be updated if the project uses different products or versions.
