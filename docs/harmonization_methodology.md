# FireLens — Harmonization Methodology

## 1. Introduction

The main objective of FireLens is to harmonize active-fire observations from MODIS and VIIRS.

Harmonization means creating a consistent framework for analyzing different satellite datasets while preserving their original characteristics.

The process does not mean treating all satellite observations as identical.

## 2. Why Harmonization Is Required

MODIS and VIIRS have different:

- Spatial resolutions.
- Observation times.
- Detection characteristics.
- Measurement attributes.
- Confidence information.
- Observation footprints.

Because of these differences, combining their records directly may produce misleading results.

FireLens uses a structured workflow to make their observations easier to compare.

## 3. Overall Workflow

```mermaid
flowchart TD
    A[MODIS Dataset] --> C[Data Validation]
    B[VIIRS Dataset] --> C

    C --> D[Preserve Original Records]
    D --> E[Normalize Common Attributes]

    E --> F[Spatial Analysis]
    E --> G[Temporal Analysis]

    F --> H[Candidate Association]
    G --> H

    H --> I[Matched and Unmatched Records]
    I --> J[Sensor Comparison]
    J --> K[Statistical Analysis]
    K --> L[Visualization]
```

## 4. Step 1: Data Collection

Collect active-fire observations from NASA FIRMS.

The project initially uses:

- MODIS active-fire observations.
- VIIRS active-fire observations.

The datasets should cover the same geographic region and a suitable time period for comparison.

Store the original datasets separately.

Record:

- Source product.
- Sensor.
- Satellite.
- Download date.
- Geographic coverage.
- Date range.
- Product version, if available.

## 5. Step 2: Data Validation

Before processing, validate the datasets.

Validation checks include:

### Coordinate Validation

Latitude must be between -90 and +90 degrees.

Longitude must be between -180 and +180 degrees.

### Timestamp Validation

Check whether the observation date and time can be parsed correctly.

### Missing Values

Identify missing values in required fields.

### Duplicate Records

Identify records that appear to be duplicated.

Duplicates should be investigated before removal.

### Data Type Validation

Ensure numeric fields contain valid numeric values.

The system should generate a validation report.

## 6. Step 3: Data Normalization

The two datasets may use different names for equivalent attributes.

Create common fields such as:

- latitude
- longitude
- acquisition_date
- acquisition_time
- satellite
- instrument
- frp
- confidence

Preserve the original field names and values separately.

Do not force incompatible attributes into the same scale.

For example, confidence values should retain their original meaning unless a scientifically justified transformation is defined.

## 7. Step 4: Spatial Association

Spatial association identifies observations that occur near one another.

For two observations with geographic coordinates:

- Observation A: latitude A, longitude A.
- Observation B: latitude B, longitude B.

Calculate the geographic distance between them using an appropriate geodesic method or a suitable projected coordinate system.

A candidate spatial match can be defined as:

\[
D(A,B) \leq D\_{\text{threshold}}
\]

Where:

- D(A,B) is the distance between observations.
- D_threshold is a configurable distance threshold.

The threshold must be selected based on product characteristics and experimental evaluation.

It should not be treated as a universal constant.

## 8. Step 5: Temporal Association

Observations may be recorded at different times.

Calculate the absolute time difference:

\[
\Delta t = |t_A-t_B|
\]

A candidate temporal match can be defined as:

\[
\Delta t \leq T\_{\text{threshold}}
\]

Where:

- Δt is the time difference.
- T_threshold is the configured time threshold.

Time zones and timestamp conventions must be handled consistently.

## 9. Step 6: Candidate Matching

A pair of observations can be considered a candidate match when both spatial and temporal conditions are satisfied.

\[
D(A,B) \leq D\_{\text{threshold}}
\]

and

\[
\Delta t \leq T\_{\text{threshold}}
\]

The result should include:

- Observation identifiers.
- Distance between observations.
- Time difference.
- Source sensors.
- Matching status.

### Matching Categories

**Matched:** Both spatial and temporal conditions are satisfied.

**Unmatched:** No suitable observation is found under the configured criteria.

**Uncertain:** The association requires further examination or is affected by ambiguous candidate relationships.

A matched pair is not proof that both sensors detected the exact same physical fire.

Multiple nearby observations may belong to one event, multiple separate events, or overlapping detection footprints.

## 10. Step 7: Sensor Comparison

After association, compare MODIS and VIIRS observations.

Possible comparisons:

- Observation counts.
- Geographic distribution.
- Time differences.
- Distance differences.
- FRP distributions.
- Detection patterns.
- Matched and unmatched records.

Measurements should only be compared directly when their definitions and units are compatible.

## 11. Step 8: Statistical Analysis

Generate useful statistics:

- Total observations.
- Daily observation counts.
- Weekly observation counts.
- Monthly observation counts.
- Sensor-wise observation counts.
- Regional distribution.
- FRP summaries.

These statistics help users understand the distribution of observed active fires.

## 12. Step 9: Anomaly Detection

FireLens can identify unusual changes in observed fire activity.

For example, if a region normally has a certain range of daily observations but suddenly records a much higher number, the system can flag the change for investigation.

A simple statistical method is the Z-score:

\[
Z = \frac{X-\mu}{\sigma}
\]

Where:

- X = current observation count.
- μ = historical mean.
- σ = historical standard deviation.

A configurable threshold can be used to flag unusual values.

The historical baseline should account for relevant seasonality and data availability.

An anomaly is an unusual observation pattern. It is not a prediction of future fires.

## 13. Step 10: Data Quality Assessment

Evaluate the processed dataset using:

- Missing-value percentage.
- Invalid coordinate count.
- Duplicate count.
- Timestamp validation errors.
- Number of successfully processed records.
- Number of rejected records.
- Sensor-wise data availability.

Display data quality information alongside the analysis.

## 14. Phase 4 Spatial-Temporal Matching Engine & Sensitivity Analysis

### 14.1 Spherical Great-Circle Distance Calculation (Distinguished from Ellipsoidal Geodesic)

Euclidean distance on raw latitude and longitude introduces severe spatial distortion, especially at higher latitudes where meridians converge ($\Delta x \propto \cos\phi$) and across the antimeridian ($\pm 180^\circ$). FireLens calculates the spherical great-circle distance using the Haversine formula with antimeridian wrap-around adjustment:

$$\Delta\lambda = (\lambda_2 - \lambda_1 + \pi) \pmod{2\pi} - \pi$$

$$a = \sin^2\left(\frac{\Delta\phi}{2}\right) + \cos\phi_1 \cos\phi_2 \sin^2\left(\frac{\Delta\lambda}{2}\right)$$

$$d = 2 \cdot R_{\text{earth}} \cdot \arctan2\left(\sqrt{a}, \sqrt{1-a}\right), \quad R_{\text{earth}} = 6371.0088\text{ km}$$

**Scientific Distinction from Ellipsoidal Geodesics:**
The Haversine formula calculates spherical great-circle distance assuming a spherical Earth of mean radius $R = 6371.0088\text{ km}$ (IUGG recommendation). It is explicitly distinguished from an ellipsoidal geodesic distance (such as Karney or Vincenty algorithms on the WGS-84 reference ellipsoid). Spherical great-circle distance differs from ellipsoidal geodesic distance by at most ~0.5% at mid-latitudes, which is negligible compared to sensor pixel footprints (1 km to 4.8 km for MODIS, 375 m to 800 m for VIIRS) and geolocation uncertainties (~500 m for MODIS, ~100 m for VIIRS). Crucially, spherical geometry enables closed-form angular metric queries natively supported by tree-based spatial indices (`BallTree` with `metric="haversine"` in radians).

### 14.2 Spatial-Temporal Candidate Generation

To scale over millions of observations without an $O(N \cdot M)$ all-pairs bottleneck:

1. **Temporal Gating:** Observations are sorted chronologically and indexed by UTC epoch seconds. For each MODIS observation at $t_{\text{modis}}$, VIIRS records are filtered using binary search to the candidate window $[t_{\text{modis}} - \Delta t_{\max}, t_{\text{modis}} + \Delta t_{\max}]$.
2. **Spatial Indexing:** A `BallTree` with the `haversine` metric is constructed over the radian coordinates of the temporally filtered VIIRS candidates, executing radius queries at $r = R_{\max} / R_{\text{earth}}$ in $O(\log K)$ time.

### 14.3 Heuristic Proximity Ranking Score

Candidate associations are ranked by an empirical proximity score:

$$\text{score} = w_{\text{spatial}} \cdot \text{spatial\_score} + w_{\text{temporal}} \cdot \text{temporal\_score}$$

$$\text{spatial\_score} = \max\left(0, 1 - \frac{d}{R_{\max}}\right), \quad \text{temporal\_score} = \max\left(0, 1 - \frac{\Delta t}{T_{\max}}\right)$$

_Important Note:_ This score is an empirical proximity ranking metric, NOT a calibrated probability of physical flame front identity.

### 14.4 Bipartite Graph Multiplicity and Ambiguity Classification

Multiplicity categories describe topological connectivity patterns within the bipartite proximity graph. They do NOT constitute verified physical fire relationships:

- **1:1 Pair Pattern:** Isolated bipartite match where exactly 1 MODIS detection and 1 VIIRS detection satisfy spatial and temporal proximity limits.
- **1:N Split Pattern:** Topological pattern where 1 MODIS detection links to $N$ VIIRS detections within threshold limits (consistent with the 7.1x nadir pixel area difference, though not definitive physical proof of flame front splitting).
- **N:1 Overlap Pattern:** Topological pattern where $N$ MODIS detections associate with 1 VIIRS detection within threshold limits.
- **M:N Cluster Pattern:** Multi-node connected bipartite subgraph where multiple detections from both sensors mutually satisfy proximity thresholds in dense wildfire zones.
- **Ambiguity Detection:** When the top two candidate associations for a given observation have heuristic scores within $\Delta \text{score} \le 0.15$, associations are classified as `ambiguous_association` rather than arbitrarily selecting one. All plausible candidate edges are preserved.

### 14.5 Real-Data Sensitivity Evaluation (12 Parameter Combinations)

Evaluated on authentic NASA FIRMS observations from the North American Boreal Forest Wildfire Complex (Saskatchewan / Manitoba, Canada: Lat 54°–58°N, Lon 106°–102°W, August 1–2, 2025; 22,455 valid records: MODIS Terra = 1,525, MODIS Aqua = 1,591, VIIRS NOAA-20 = 19,339):

| Spatial Radius ($R$) | Temporal Window ($T$) | Candidate Associations | Unique Matched MODIS | Unique Matched VIIRS | MODIS Ambiguity Rate | Mean Distance | Mean $\Delta t$ | Candidates / Matched MODIS |
| :------------------- | :-------------------- | :--------------------- | :------------------- | :------------------- | :------------------- | :------------ | :-------------- | :------------------------- |
| **1.25 km**          | 15 min                | 7,301                  | 620 (19.90%)         | 3,143 (16.25%)       | 89.68%               | 0.793 km      | 7.95 min        | 11.78                      |
| **1.25 km**          | 30 min                | 10,704                 | 1,050 (33.70%)       | 4,723 (24.42%)       | 88.38%               | 0.791 km      | 14.58 min       | 10.19                      |
| **1.25 km**          | 60 min                | 14,665                 | 1,427 (45.80%)       | 6,842 (35.38%)       | 87.11%               | 0.786 km      | 22.22 min       | 10.28                      |
| **1.25 km**          | 90 min                | 16,927                 | 1,735 (55.68%)       | 7,939 (41.05%)       | 86.51%               | 0.785 km      | 30.37 min       | 9.76                       |
| **2.00 km**          | 15 min                | 14,858                 | 632 (20.28%)         | 3,657 (18.91%)       | 97.31%               | 1.220 km      | 7.95 min        | 23.51                      |
| **2.00 km**          | 30 min                | 21,372                 | 1,078 (34.60%)       | 5,648 (29.21%)       | 95.64%               | 1.211 km      | 14.29 min       | 19.83                      |
| **2.00 km**          | **60 min (Baseline)** | **28,911**             | **1,470 (47.18%)**   | **8,328 (43.06%)**   | **94.42%**           | **1.202 km**  | **21.82 min**   | **19.67**                  |
| **2.00 km**          | 90 min                | 33,247                 | 1,801 (57.80%)       | 9,653 (49.91%)       | 94.39%               | 1.200 km      | 29.86 min       | 18.46                      |
| **3.50 km**          | 15 min                | 31,933                 | 644 (20.67%)         | 4,155 (21.49%)       | 98.29%               | 2.042 km      | 7.95 min        | 49.59                      |
| **3.50 km**          | 30 min                | 44,735                 | 1,099 (35.27%)       | 6,498 (33.60%)       | 97.91%               | 2.018 km      | 13.87 min       | 40.71                      |
| **3.50 km**          | 60 min                | 59,047                 | 1,500 (48.14%)       | 9,760 (50.47%)       | 96.67%               | 1.993 km      | 20.96 min       | 39.36                      |
| **3.50 km**          | 90 min                | 67,111                 | 1,847 (59.27%)       | 11,270 (58.28%)      | 96.32%               | 1.981 km      | 28.51 min       | 36.34                      |

### 14.6 Benchmark Disentanglement and Performance Measurements

To maintain scientific rigor, benchmark metrics are strictly separated between single-pass baseline matching and multi-pass sensitivity evaluation:

- **Baseline Matching Execution ($R = 2.0\text{ km}, \Delta t = 60\text{ min}$):**
  - Candidate Generation: $14.77\text{ s}$
  - Association Processing & Ambiguity Classification: $0.94\text{ s}$
  - Total Baseline Matching Time: $15.71\text{ s}$
  - Baseline Candidate Throughput: $28,911 \text{ candidate pairs} / 15.71\text{ s} \approx 1,840.3 \text{ pairs/sec}$
  - Baseline Observation Throughput: $22,455 \text{ input observations} / 15.71\text{ s} \approx 1,429.3 \text{ obs/sec}$
- **Sensitivity Grid Evaluation:** Running all 12 combinations required $190.32\text{ s}$. Total pipeline workflow runtime was $206.03\text{ s}$.
- **Throughput Calculation Audit:** Conflating the baseline candidate count (28,911) with total multi-pass grid runtime (206s) produced an uncalibrated quotient of ~138–140 assoc/s. Throughput is now accurately reported for the baseline execution.

### 14.7 Comparative Savanna Region Analysis & Overpass Geometry

In the secondary test region (Southern African Savanna / Miombo Belt: Lat 12°–15°S, Lon 22°–26°E, August 1–2, 2025; 4,599 valid records: MODIS Aqua = 917, MODIS Terra = 38, VIIRS NOAA-20 = 3,644):
- Candidate Associations Found: 16 (MODIS match rate: 0.73%, VIIRS match rate: 0.25%).
- **Primary Governing Factor (Orbital Geometry):** Sun-synchronous polar orbits create systematic overpass timing gaps. Terra overpasses at ~10:30 local solar time, whereas Aqua and NOAA-20 overpass in early afternoon (~13:30 local solar time), resulting in an inherent ~3-hour diurnal temporal gap. In this Savanna study area, VIIRS NOAA-20 overpassed predominantly at ~16:00 UTC and MODIS Aqua at ~18:00 UTC (~2-hour gap), so very few detections fell within the 60-minute matching window regardless of physical fire behavior.
- **Secondary Hypothesis:** Rapid savanna grass fire spread and shorter flaming residence times may further reduce chances of persistence between non-coincident passes, but orbital overpass geometry is the primary governing constraint.

## 15. Expected Output

The harmonization process produces:

1. Validated MODIS records.
2. Validated VIIRS records.
3. Normalized observations.
4. Matched observation relationships.
5. Unmatched observations.
6. Sensor comparison results.
7. Activity statistics.
8. Anomaly results.
9. Data quality reports.

## 16. Scientific Limitations

- Satellite observations are not continuous ground observations.
- Different instruments have different detection characteristics.
- A spatial-temporal match does not prove physical fire identity.
- Active-fire points are not fire perimeters.
- FRP is not burned area.
- Cloud cover and observation timing can affect detection.
- Confidence values may not be directly comparable.
- Thresholds influence association results.
- Anomaly detection does not guarantee future fire activity.

## 17. Conclusion

FireLens provides a transparent and reproducible methodology for analyzing MODIS and VIIRS active-fire observations.

By preserving source information, normalizing common attributes, associating potentially related observations, and evaluating data quality, the platform supports more meaningful cross-sensor analysis.
