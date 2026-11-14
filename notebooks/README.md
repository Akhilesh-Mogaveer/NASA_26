# FireLens Scientific Exploratory Data Analysis (EDA)

This directory contains the primary scientific analysis notebook for **FireLens**, developed for the **NASA Space Apps Challenge 2026** (Challenge: *Harmonization of MODIS and VIIRS Hot Spots*).

## Notebook File
- **[`FireLens_EDA.ipynb`](./FireLens_EDA.ipynb)**: Fully executed Jupyter Notebook analyzing 22,175,341 authentic NASA FIRMS observations from the 2025 calendar year (46 cells with embedded high-resolution figures).

---

## 1. Scientific Overview & Objectives

MODIS (Terra & Aqua, 1km resolution) and VIIRS (NOAA-20, 375m resolution) represent two distinct generations of spaceborne thermal radiometry. Comparing their active fire detections requires rigorous physical understanding:
- **Spatial Resolution & Footprint Growth:** 1km nadir vs. 375m nadir; scan-edge bow-tie expansion (VIIRS limits area growth to ~4x via onboard aggregation, while MODIS expands ~10x).
- **Fire Radiative Power (FRP):** Instantaneous thermal power output (MW) at satellite overpass. Minimum detection limits: ~8–10 MW for MODIS vs. ~0.5–1 MW for VIIRS due to sub-pixel thermal dilution.
- **Diurnal Sampling:** Sun-synchronous equator crossings (~10:30 Terra, ~13:30 Aqua and NOAA-20).
- **Confidence Semantics:** Continuous percentage (0–100%) vs. categorical flags (`'l'`, `'n'`, `'h'`), which represent fundamentally separate algorithmic conventions.

---

## 2. Notebook Structure (13 Audited Scientific Sections)

1. **Executive Summary & Scientific Purpose:** Problem statement, remote sensing physics, snapshot nature of observations, and scope.
2. **Dataset Overview, Setup & Data Validity Audit:**
   - Zero-copy DuckDB columnar connection.
   - Complete census of 22,175,341 records (22,175,332 valid, 9 invalid).
   - Explicit documentation of flagged records: 1 MODIS negative FRP (-5.9 MW) and 8 VIIRS spatial-temporal duplicates on identical coordinates and times.
   - Sensitivity check: demonstrating negligible difference (<0.0001 MW) between valid-only and all-record analyses.
3. **Volume & Scale Comparison:** The **4.979x** VIIRS-to-MODIS observation discrepancy (18.47M vs. 3.71M); dual bar and donut charts.
4. **Complete Temporal Distribution Analysis:**
   - Continuous 365-day daily observation trend time-series for 2025.
   - 12-month seasonal cycles and monthly day vs. night stacked breakdown.
   - Global UTC hourly distribution vs. Estimated Local Solar Time (LST) distribution ($\text{LST} \approx \text{UTC} + \text{lon}/15^\circ$), identifying true local early afternoon overpass peaks.
   - Day-of-week distribution (Monday through Sunday).
5. **Fire Radiative Power (FRP) Analysis — Physical Formulation:**
   - Parametric and non-parametric metrics (mean, median, IQR, 95th/99th percentiles).
   - Crucial scientific correction: FRP is instantaneous power (MW), not energy (MJ); snapshot power sums cannot be equated with continuous Fire Radiative Energy (FRE).
   - Log-transformed probability densities (KDE) and empirical Cumulative Distribution Functions (CDF) ($N=100,000$ valid sample per sensor).
   - Sub-pixel thermal dilution explanation: higher MODIS mean FRP does not indicate higher flame intensity.
6. **Brightness Temperature Analysis:** Mid-infrared 4µm channel distributions, Planck blackbody relation, and saturation limits (VIIRS I-4 at ~367 K vs. MODIS Band 21 up to ~500 K).
7. **Complete Geographical Distribution & Spatial Clustering:**
   - 2-degree equirectangular grid definition and **poleward area distortion caveat** ($\text{area} \propto \cos\phi$, shrinking by 50% at 60° latitude).
   - Sensor-specific spatial density maps: side-by-side MODIS 2° density vs. VIIRS 2° density.
   - Top 10 density regions identified by exact latitude/longitude coordinate bounds (without unverified political labels).
   - Latitudinal profile (5° bands) comparing Tropical savanna and Boreal fire belts.
8. **Separate Sensor Confidence Analysis & Conventions:**
   - Separate analysis of MODIS continuous numeric confidence (0–100%) vs. VIIRS categorical flags (`'l'`, `'n'`, `'h'`).
   - Explicit disclaimer that analyst-defined exploratory bins (<30, 30–79, ≥80) are **not** equivalent to VIIRS native classes.
9. **Multi-Sensor Discrepancy & Footprint Geometry Analysis:** Footprint area ratios, edge-of-scan aggregation, and schematic footprint diagram.
10. **Scientific Findings Taxonomy:** Clean 4-tier separation: Direct Observations, Statistical Descriptions, Scientific Interpretations, and Hypotheses Requiring Further Investigation.
11. **Candidate Starting Hypotheses for Phase 4 Harmonization:**
    - Explicitly designated as *candidate starting hypotheses*, NOT validated optimal parameters.
    - Proposed candidate spatial search radius ($R_{\text{match}} \approx 1.25\text{--}3.5\text{ km}$), $N:1$ clustering, and temporal window gating ($\Delta t \le 90\text{ min}$).
    - Systematic Phase 4 evaluation protocol outlined (distance sensitivity, false vs. missed match trade-offs).
12. **Reusable Analytical Outputs Generator:** Standalone executable function inside the notebook that refreshes all 8 analytical artifacts in `data/analytics/` directly from the unified catalog.
13. **Scientific References & Citations:** Full academic citations (Giglio et al. 2016; Schroeder et al. 2014; Wooster et al. 2003, 2005; Kaufman et al. 1998; NASA FIRMS documentation).

---

## 3. How to Run the Notebook

### Prerequisites
Ensure your backend virtual environment is active with all scientific dependencies installed:
```powershell
.\backend\venv\Scripts\activate
python -c "import duckdb, pandas, numpy, matplotlib, seaborn, nbformat; print('Ready!')"
```

### Option A: Launch in Jupyter Lab / Notebook
```powershell
# From repository root
jupyter lab notebooks/FireLens_EDA.ipynb
```

### Option B: Non-Interactive Re-Execution via CLI
To re-execute all 46 cells and refresh all embedded charts from raw data:
```powershell
jupyter nbconvert --to notebook --execute notebooks/FireLens_EDA.ipynb --output FireLens_EDA.ipynb
```

---

## 4. Key Empirical Findings Summary

| Metric | MODIS C6.1 | VIIRS C2 (NOAA-20) | Multi-Sensor Relationship | Physical & Algorithmic Root Cause |
| :--- | :--- | :--- | :--- | :--- |
| **Valid Observation Count** | 3,708,771 | 18,466,561 | VIIRS detects **4.979x** more fires | 375m spatial resolution ($7.11\times$ smaller area) + gapless $3,040\text{ km}$ swath. |
| **Mean FRP** | 41.21 MW | 9.68 MW | MODIS mean is **4.25x** higher | Sub-pixel thermal dilution: small fires (<5 MW) fail to trigger MODIS's 1km threshold. |
| **Median FRP** | 17.90 MW | 5.05 MW | VIIRS detects far cooler fires | VIIRS minimum detectable FRP is ~0.5–1.0 MW compared to ~8–10 MW for MODIS. |
| **Sum of Reported FRP** | 152.82M MW | 178.84M MW | Snapshot power sum (+17.0%) | Reflects footprint sampling and sub-pixel detection; does not represent total energy (FRE in MJ). |
| **Diurnal Overpass Peak** | ~10:30 & ~13:30 LST | ~13:30 LST | Afternoon overpass alignment | Local solar time overpass aligns with peak diurnal temperatures and fuel drying. |
| **Data Integrity Rate** | 99.99997% | 99.99996% | 9 flagged records preserved | 1 negative MODIS FRP (-5.9 MW), 8 VIIRS ST duplicates. Zero missing coordinates. |
