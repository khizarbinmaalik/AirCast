# AirCast — 3-Day AQI Forecasting for Sukkur, Pakistan

An end-to-end MLOps project that forecasts Air Quality Index (AQI) up to three days ahead, built as my project for the 10Pearls Shine Internship Program (Data Sciences track).

**Live dashboard:** [aircast-aqi.streamlit.app](https://aircast-aqi.streamlit.app)
**Full report:** [FINAL_SUBMISSION_REPORT.pdf](FINAL_SUBMISSION_REPORT.pdf)
**Full methodology log:** [docs/EDA_Findings.md](docs/EDA_Findings.md)

---

## What it does

AirCast pulls live weather, pollutant, and satellite fire-detection data, engineers a feature set grounded in the seasonal and atmospheric patterns behind Sukkur's air quality, and forecasts AQI 1, 2, and 3 days ahead using a gradient-boosted model trained to predict *change* from current conditions rather than the absolute value directly. The whole pipeline — data ingestion, retraining, and deployment — runs on its own, on a schedule, with no manual steps.

The dashboard shows the current AQI, a 3-day forecast with hazardous-air alerts, a 24-hour trend chart, and a live SHAP breakdown explaining exactly what's driving each forecast.

## Results

Measured on a chronological (never shuffled) test split — the model has never seen these weeks during training or tuning.

| Model | Day 1 R² | Day 2 R² | Day 3 R² |
|---|---|---|---|
| Naive baseline (persistence) | 0.41 | -0.02 | -0.27 |
| Ridge regression | 0.46 | 0.04 | -0.18 |
| Random Forest (tuned) | 0.49 | 0.14 | -0.02 |
| XGBoost (absolute target) | 0.52 | 0.17 | 0.02 |
| **XGBoost (delta target) — final** | **0.58** | **0.22–0.23** | **0.07–0.10** |

The 3-day horizon is the hardest target in the project — by the time you're forecasting 3 days out, the strongest signal (recent AQI) has mostly decayed, and the model has to lean on weaker seasonal and atmospheric proxies instead. Getting that from a *negative* R² (worse than guessing the average) to a genuine, if modest, positive one took a documented sequence of roughly a dozen modeling experiments — see the report for the full trail, including what didn't work.

## Architecture

```
                    ┌─────────────────┐         ┌──────────────────┐
  Open-Meteo   ───▶ │  Hourly Feature  │ ───▶    │  Hopsworks        │
  NASA FIRMS        │  Pipeline        │         │  Feature Store    │
                    │  (GitHub Actions)│         └────────┬──────────┘
                    └─────────────────┘                  │
                                                           ▼
                    ┌─────────────────┐         ┌──────────────────┐
                    │  Daily Training  │ ◀────── │  reads latest     │
                    │  Pipeline        │         │  feature set       │
                    │  (GitHub Actions)│         └──────────────────┘
                    └────────┬─────────┘
                             ▼
                    ┌─────────────────┐         ┌──────────────────┐
                    │  Hopsworks       │ ───▶    │  Streamlit         │
                    │  Model Registry  │         │  Dashboard         │
                    └─────────────────┘         │  (live inference,  │
                                                  │  SHAP, alerts)     │
                                                  └──────────────────┘
```

**Feature pipeline** (hourly): fetches current AQI, weather, and fire-activity data, engineers the full feature set, and inserts it into Hopsworks. Detects gaps since its last successful run and automatically widens its fetch window to close them — verified resilient to real transient API failures, not just in theory.

**Training pipeline** (daily): reads the current feature set from Hopsworks, retrains all three horizon models, and registers the new version in the Hopsworks Model Registry with its evaluation metrics attached.

**Dashboard**: loads the latest registered model, fetches current conditions independently (a lighter-weight path than the training pipeline, since inference doesn't need historical targets), and serves a live forecast with explainability.

## Tech stack

- **Data**: Open-Meteo (weather + air quality, historical + live), NASA FIRMS (satellite fire detection)
- **Feature store & model registry**: Hopsworks
- **Modeling**: XGBoost, scikit-learn, SHAP
- **Automation**: GitHub Actions
- **Dashboard**: Streamlit, Plotly, deployed on Streamlit Community Cloud

## Key findings

A few of the more interesting results from the full methodology log:

- AQI in Sukkur follows a strong seasonal cycle — a monsoon trough (July–September) and a winter peak (October–January) driven by crop-residue burning and temperature inversions.
- Reformulating the prediction target from "tomorrow's AQI" to "the *change* in AQI from today" was the single biggest modeling improvement in the project — more effective than any amount of hyperparameter tuning.
- A diagnostic test comparing a chronological train/test split against a randomly shuffled one showed the shuffled version inflating R² from ~0.02–0.58 to ~0.87–0.93 on the same model — a useful check against a common and easy-to-make mistake in time series evaluation.
- SHAP revealed that short-term AQI lags (1–3 hours) and long-term lags (48–72 hours) push predictions in *opposite* directions — recent spikes tend to mean-revert, while AQI that's stayed elevated for days looks like a sustained pollution episode likely to continue.

Full reasoning, including experiments that didn't work (and why), is in [docs/EDA_Findings.md](docs/EDA_Findings.md).

## Project structure

```
├── app/                   # Streamlit dashboard
├── src/                   # Shared pipeline code (data fetching, feature
│                            engineering, Hopsworks client, inference)
├── pipelines/              # Feature pipeline (hourly) and backfill pipeline
├── training/                # Production training script and model registration
├── experiments/            # Tested-and-not-adopted models and approaches,
│                            kept for reproducibility
├── docs/                    # EDA findings log, project report, SHAP figures
├── notebooks/                # Exploratory notebook
└── .github/workflows/         # GitHub Actions automation
```

## Running it locally

```bash
git clone https://github.com/khizarbinmaalik/AQI-Predictor.git
cd AQI-Predictor
pip install -r requirements.txt
```

Create a `.env` file with:
```
HOPSWORKS_API_KEY=your_key
FIRMS_MAP_KEY=your_key
```

Then:
```bash
streamlit run app/streamlit_app.py
```

## Limitations

- The 3-day forecast, while genuinely better than baseline, remains the weakest of the three — a real limit on how far ahead AQI is predictable from the features used here, not something I expect further tuning to close.
- Reported metrics drift slightly between backfill runs, since the training window is anchored to the current date rather than a fixed historical range.
- Hosted on Streamlit Community Cloud's free tier, so the dashboard may need a manual wake-up click after periods of inactivity.

Full discussion of these and other tradeoffs is in the [project report](docs/AirCast_Project_Report.pdf).

## Author

**Muhammad Khizar Bin Malik**
BS Computer Science (AI), Sukkur IBA University
10Pearls Shine Internship Program — Data Sciences Track