import json
import pandas as pd
import hopsworks
from xgboost import XGBRegressor

from src.fetch_data import fetch_aqi_data, fetch_weather_data
from src.fire_data_fetch import fetch_recent_fire_data, aggregate_daily_fire_features
from src.feature_engineering import merge_data, engineer_features, merge_fire_features
from src.config import HOPSWORKS_API_KEY, LATITUDE, LONGITUDE

MODEL_NAME = "aqi_xgboost_delta"


def fetch_current_features(latitude=LATITUDE, longitude=LONGITUDE, past_days=5):
    """
    Fetches the most recent feature row for live inference.
    past_days=5 gives enough history to compute the 72h lag feature on
    the latest row (72h = 3 days, +2 days safety margin).
    """

    aqi_df = fetch_aqi_data(latitude, longitude, past_days=past_days, forecast_days=0)
    weather_df = fetch_weather_data(latitude, longitude, past_days=past_days, forecast_days=0)
    merged_df = merge_data(aqi_df, weather_df)

    features_df = engineer_features(merged_df)

    fire_df = fetch_recent_fire_data(days_back=past_days)
    daily_fire_df = aggregate_daily_fire_features(fire_df)
    features_df = merge_fire_features(features_df, daily_fire_df)

    # Drop only rows missing LAG features 
    features_df = features_df.dropna().reset_index(drop=True)

    if len(features_df) == 0:
        raise Exception("No valid feature row available — insufficient recent data.")

    latest_row = features_df.iloc[[-1]]  # double brackets: keep it a DataFrame, not a Series
    return latest_row


def load_latest_model():
    project = hopsworks.login(api_key_value=HOPSWORKS_API_KEY)
    mr = project.get_model_registry()

    # Get the latest model version from the registry
    all_versions = mr.get_models(MODEL_NAME)
    model_meta = max(all_versions, key=lambda m: m.version)

    model_dir = model_meta.download()

    models = {}
    for horizon in [1, 2, 3]:
        booster = XGBRegressor()
        booster.load_model(f"{model_dir}/model_day{horizon}.json")
        models[f"day{horizon}"] = booster

    with open(f"{model_dir}/feature_columns.json") as f:
        feature_cols = json.load(f)

    print(f"Loaded model version {model_meta.version}")
    return models, feature_cols


def predict_forecast(feature_row, models, feature_cols):

    current_aqi = feature_row["us_aqi"].iloc[0]
    X = feature_row[feature_cols]

    forecast = {"current_aqi": float(current_aqi)}

    for horizon in [1, 2, 3]:
        predicted_delta = models[f"day{horizon}"].predict(X)[0]
        predicted_aqi = current_aqi + predicted_delta
        forecast[f"day{horizon}"] = float(predicted_aqi)

    return forecast


if __name__ == "__main__":
    feature_row = fetch_current_features()
    print("Latest feature row timestamp:", feature_row["time"].iloc[0])

    models, feature_cols = load_latest_model()
    forecast = predict_forecast(feature_row, models, feature_cols)

    print("\n--- 3-Day AQI Forecast ---")
    print(f"Current AQI: {forecast['current_aqi']:.0f}")
    print(f"Day 1: {forecast['day1']:.2f}")
    print(f"Day 2: {forecast['day2']:.2f}")
    print(f"Day 3: {forecast['day3']:.2f}")