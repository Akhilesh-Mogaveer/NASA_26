# FireLens Scientific Exploratory Data Analysis (EDA)

This directory contains the primary scientific analysis notebook for **FireLens**, developed for the **NASA Space Apps Challenge 2026** (Challenge: *Harmonization of MODIS and VIIRS Hot Spots*).

## Notebook File
- **[`FireLens_EDA.ipynb`](./FireLens_EDA.ipynb)**: Executable, self-contained Jupyter Notebook analyzing 22,175,341 authentic NASA FIRMS observations from the 2025 calendar year.

---

## 1. Scientific Overview & Objectives

MODIS (Terra & Aqua, 1km resolution) and VIIRS (NOAA-20, 375m resolution) represent two distinct generations of spaceborne thermal radiometry. Comparing their active fire detections requires an understanding of:
- **Spatial Resolution & Footprint Growth:** 1km nadir vs. 375m nadir; bow-tie pixel expansion.
- **Fire Radiative Power (FRP):** Minimum detection limits (~8–10 MW for MODIS vs. ~0.5–1 MW for VIIRS).
- **Diurnal Sampling:** Solar-synchronous equator crossings (10:30, 13:30).
- **Confidence Semantics:** Continuous percentage (0–100%) vs. categorical flags (`'l'`, `'n'`, `'h'`).

This notebook evaluates these characteristics across the complete 2025 NASA FIRMS dataset to lay empirical foundations for the Phase 4 Harmonization Engine.

---

## 2. Notebook Structure (12 Analytical Sections)

1. **Executive Summary & Scientific Purpose:** Context, satellite sensor overview, problem statement, and scope.
2. **Dataset Overview & Schema Inspection:** DuckDB zero-copy connection, catalog schema discovery, data sampling.
3. **Volume & Scale Comparison:** Detailed breakdown of the **4.979x** VIIRS-to-MODIS observation discrepancy (18.47M vs. 3.71M).
4. **Temporal Distribution Analysis:**
   - 2025 monthly seasonal trends.
   - Diurnal cycle (00:00–23:00 UTC hourly distribution).
   - Daytime vs. Nighttime distribution (~70% day, ~30% night).
5. **Fire Radiative Power (FRP) Analysis:**
   - Parametric and non-parametric metrics (mean, median, IQR, 95th/99th percentiles).
   - Log-transformed probability densities (KDE) and empirical Cumulative Distribution Functions (CDF).
   - Radiated Energy Convergence: MODIS 152.8M MW vs. VIIRS 178.8M MW (+17% difference despite 5x count).
6. **Brightness Temperature Analysis:** Mid-infrared 4µm channel distributions, Planck blackbody relation, sensor saturation thresholds.
7. **Geographical Distribution & Spatial Clustering:**
   - Global 2-degree grid cell density mapping.
   - Latitudinal profile (Tropical savanna vs. Boreal wildfire zones).
   - Top 10 most active global fire hotspots in 2025.
8. **Observation Quality & Confidence Breakdown:** Harmonization of continuous MODIS scores into categorical levels (Low, Nominal, High).
9. **Multi-Sensor Discrepancy & Footprint Geometry Analysis:** Physical mechanisms behind detection differences; nadir vs. scan edge footprint geometry diagram.
10. **Key Insights & Empirical Findings:** Synthesis table linking quantitative findings to physical causes and operational implications.
11. **Implications for Harmonization (Phase 4 Foundation):** Spatial association radii, $N:1$ clustering architecture, temporal window gating, and non-destructive provenance tracking.
12. **References & Scientific Provenance:** Giglio et al. (2016), Schroeder et al. (2014), Wooster et al. (2003, 2005), and NASA FIRMS documentation.

---

## 3. How to Run the Notebook

### Prerequisites
Ensure your backend virtual environment is active with all scientific dependencies installed:
```bash
# Windows PowerShell
.\backend\venv\Scripts\Activate.ps1

# Verify dependencies
python -c "import duckdb, pandas, numpy, matplotlib, seaborn, nbformat; print('Ready!')"
```

### Option A: Launch in Jupyter Lab / Notebook
```bash
# From repository root
jupyter lab notebooks/FireLens_EDA.ipynb
# Or
jupyter notebook notebooks/FireLens_EDA.ipynb
```

### Option B: Non-Interactive Re-Execution via CLI
To re-execute all 29 cells and refresh all embedded charts from raw data:
```bash
jupyter nbconvert --to notebook --execute notebooks/FireLens_EDA.ipynb --output FireLens_EDA.ipynb
```

---

## 4. Key Empirical Findings Summary

| Metric | MODIS C6.1 | VIIRS C2 (NOAA-20) | Multi-Sensor Relationship |
| :--- | :--- | :--- | :--- |
| **Observation Count** | 3,708,771 | 18,466,561 | VIIRS detects **4.979x** more hot spots |
| **Mean FRP** | 41.21 MW | 9.68 MW | MODIS mean is **4.25x** higher |
| **Median FRP** | 17.90 MW | 5.05 MW | VIIRS detects far cooler/smaller fires |
| **Total Radiated Energy** | 152.82M MW | 178.84M MW | Only **17.0%** difference globally |
| **Nadir Spatial Resolution** | 1,000 m | 375 m | Pixel area ratio: **7.11x** |
| **Data Integrity Rate** | >99.999% | >99.999% | 0 invalid coords, 100% valid timestamps |
