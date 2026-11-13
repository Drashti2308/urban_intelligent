# Urban Infrastructure Pulse Intelligence

An intelligent urban infrastructure analysis and decision-support application using NYC 311 service complaint data.

The project combines data processing, spatial analysis, machine learning, and an interactive Streamlit dashboard to explore infrastructure patterns and support investigation and recommendations.

## 1. Key Features

- Interactive Streamlit dashboard
- NYC 311 infrastructure complaint analysis
- DBSCAN-based spatial hotspot analysis
- K-Means-based area profiling
- Geographic visualization with PyDeck
- NYC borough and ZCTA geographic validation
- New complaint batch processing
- Infrastructure investigation and recommendation services

## 2. Technology Stack

**Language:** Python 3.12.13 (current development environment)

**User Interface:** Streamlit, PyDeck

**Data Processing:** Pandas, NumPy

**Machine Learning:** Scikit-learn, Joblib

**Geospatial Processing:** GeoPandas, Shapely

**Additional Dependency:** Threadpoolctl

## 3. Project Structure

```text
Urban-Infrastructure-Pulse-Intelligence/
├── config/
├── dashboard/
│   └── urban_pulse_simple.py
├── data/
├── kmeans_results/
├── logs/
├── models/
├── notebooks/
├── outputs/
├── src/
│   ├── data/
│   ├── features/
│   ├── integration/
│   ├── models/
│   ├── preprocessing/
│   ├── recommendations/
│   └── ui/
├── tests/
├── README.md
└── requirements.txt
```

## 4. Installation

Use a Python environment compatible with the project's dependencies.

The current working development environment uses Python 3.12.13.

From the project root directory, install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

**Note:** Fresh-environment installation and dependency compatibility have not yet been fully validated.

## 5. Run the Final Dashboard

Open a terminal in the project root directory.

Execute:

```powershell
python -m streamlit run dashboard/urban_pulse_simple.py
```

Open the local URL displayed in the terminal, typically:

```text
http://localhost:8501
```

This is the confirmed final GUI entry point.

## 6. Required Backend Artifacts

The application requires model, table, and geographic reference files.

The backend's artifact validation identifies these required resources:

```text
models/dbscan/primary_f_core_lookup_v1.joblib

outputs/tables/dbscan/

models/geography/nyc_borough_boundaries_gthc-hcne_v1.geojson

outputs/tables/dbscan/dbscan_action_taxonomy_v1.csv

outputs/tables/kmeans/kmeans_full_data_k3_descriptive_profiles.csv

models/geography/nyc_zcta_35j5-n34v_snapshot_2026_v1.geojson
```

These resources were found in the development environment and must be preserved during project cleanup.

## 7. Data and Analysis

The project analyzes NYC 311 service complaints, including historical infrastructure reporting data for 2023–2025.

Its analytical components include spatial clustering, area-level profiling, geographic validation, and recommendation services.

Some model and table artifacts are required for dashboard operation.

## 8. Validation Status

Confirmed during the cleanup review:

- Final Streamlit dashboard starts successfully in the existing development environment.
- Six backend resources required by the artifact checker are present.
- Python 3.12.13 is the current development version.
- Initial Python dependency list has been prepared.

Still pending:

- Fresh-environment dependency installation
- Fresh-clone application testing
- Automated test execution
- Full dashboard regression testing
- Safe cleanup of backup and legacy files
- Review of large data and output artifacts

## 9. Development and Cleanup

Project cleanup is being performed on the `audit-cleanup` Git branch.

The `full-project-upload` branch is retained as the pre-cleanup reference.

Do not remove model, geography, data, or output files until their dependencies have been reviewed and the application has been retested.