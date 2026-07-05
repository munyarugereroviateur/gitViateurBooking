"""
SkyBook - Flight Delay Prediction Model Training
==================================================
Trains a RandomForestClassifier to predict flight delay probability using:
  1. Origin and destination airports (+ distance derived from geolocation)
  2. Time of day and day of week
  3. Weather conditions (temperature, precipitation, snow, wind, pressure)
  4. Aircraft type and age
  5. Historical delay patterns (route-level and airline-level delay rates)

Run this ONCE offline (not inside Django) to produce a saved model file.
Django will just load the saved model and call .predict_proba() at request time.

Usage:
    pip install pandas numpy scikit-learn joblib --break-system-packages
    python train_delay_model.py
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import OrdinalEncoder
from sklearn.metrics import classification_report, roc_auc_score
import joblib
import os

# ---------------------------------------------------------------------------
# 1. CONFIG - adjust these paths to wherever your CSVs live on the server
# ---------------------------------------------------------------------------
FLIGHTS_PATH = r"D:\personal\UR _Data Science\All Caurses\Dr Bugingo\exam\US_flights_2023.csv"
WEATHER_PATH = r"D:\personal\UR _Data Science\All Caurses\Dr Bugingo\exam\weather_meteo_by_airport.csv"
GEO_PATH = r"D:\personal\UR _Data Science\All Caurses\Dr Bugingo\exam\airports_geolocation.csv"
OUTPUT_DIR = "model_artifacts"
DELAY_THRESHOLD_MIN = 15  # industry standard definition of "delayed"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# 2. LOAD DATA
# ---------------------------------------------------------------------------
print("Loading data...")
flights = pd.read_csv(FLIGHTS_PATH)
flights["FlightDate"] = pd.to_datetime(flights["FlightDate"])

geo = pd.read_csv(GEO_PATH, encoding="utf-8-sig")
geo = geo.rename(columns={"IATA_CODE": "airport_code"})

weather = pd.read_csv(WEATHER_PATH)
weather["time"] = pd.to_datetime(weather["time"])

# ---------------------------------------------------------------------------
# 3. FEATURE ENGINEERING
# ---------------------------------------------------------------------------
print("Engineering features...")

# --- 3a. Target variable ---
flights["is_delayed"] = (flights["Dep_Delay"] > DELAY_THRESHOLD_MIN).astype(int)

# --- 3b. Distance via haversine using origin/destination coordinates ---
geo_lookup = geo.set_index("airport_code")[["LATITUDE", "LONGITUDE"]]

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # km
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))

flights = flights.merge(
    geo_lookup.rename(columns={"LATITUDE": "dep_lat", "LONGITUDE": "dep_lon"}),
    left_on="Dep_Airport", right_index=True, how="left"
)
flights = flights.merge(
    geo_lookup.rename(columns={"LATITUDE": "arr_lat", "LONGITUDE": "arr_lon"}),
    left_on="Arr_Airport", right_index=True, how="left"
)
flights["distance_km"] = haversine(
    flights["dep_lat"], flights["dep_lon"], flights["arr_lat"], flights["arr_lon"]
)

# --- 3c. Weather join (on departure airport + date) ---
weather_small = weather.rename(columns={"airport_id": "Dep_Airport", "time": "FlightDate"})
flights = flights.merge(
    weather_small[["Dep_Airport", "FlightDate", "tavg", "tmin", "tmax", "prcp", "snow", "wdir", "wspd", "pres"]],
    on=["Dep_Airport", "FlightDate"], how="left"
)
# Fill missing weather (e.g. airport not in weather file) with column median
weather_cols = ["tavg", "tmin", "tmax", "prcp", "snow", "wdir", "wspd", "pres"]
for col in weather_cols:
    flights[col] = flights[col].fillna(flights[col].median())

# --- 3d. Historical delay-rate features (route-level and airline-level) ---
# Computed from the training data itself: how often has this route/airline been delayed historically.
route_delay_rate = flights.groupby(["Dep_Airport", "Arr_Airport"])["is_delayed"].transform("mean")
airline_delay_rate = flights.groupby("Airline")["is_delayed"].transform("mean")
airport_delay_rate = flights.groupby("Dep_Airport")["is_delayed"].transform("mean")
flights["route_historical_delay_rate"] = route_delay_rate
flights["airline_historical_delay_rate"] = airline_delay_rate
flights["dep_airport_historical_delay_rate"] = airport_delay_rate

# --- 3e. Time of day / day of week ---
# DepTime_label is already categorical (Morning/Afternoon/Evening/Night)
# Day_Of_Week already numeric (1-7)

# ---------------------------------------------------------------------------
# 4. SELECT FINAL FEATURES
# ---------------------------------------------------------------------------
categorical_features = [
    "Dep_Airport", "Arr_Airport", "DepTime_label", "Airline",
    "Manufacturer", "Model",
]
numeric_features = [
    "Day_Of_Week", "distance_km", "Aicraft_age",
    "tavg", "tmin", "tmax", "prcp", "snow", "wdir", "wspd", "pres",
    "route_historical_delay_rate", "airline_historical_delay_rate",
    "dep_airport_historical_delay_rate",
]

model_df = flights[categorical_features + numeric_features + ["is_delayed"]].dropna()
print(f"Training rows after dropping NA: {len(model_df)}")

X = model_df[categorical_features + numeric_features]
y = model_df["is_delayed"]

# --- Encode categoricals (ordinal encoding works fine for tree models) ---
encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
X_cat_encoded = encoder.fit_transform(X[categorical_features])
X_encoded = pd.DataFrame(X_cat_encoded, columns=categorical_features, index=X.index)
X_encoded[numeric_features] = X[numeric_features].values

# ---------------------------------------------------------------------------
# 5. TRAIN / VALIDATION / TEST SPLIT (70% / 15% / 15%) + TRAINING
# ---------------------------------------------------------------------------
# Step 1: split off 70% train, 30% temp (which becomes validation + test)
X_train, X_temp, y_train, y_temp = train_test_split(
    X_encoded, y, test_size=0.30, random_state=42, stratify=y
)
# Step 2: split the 30% temp evenly into 15% validation and 15% test
X_val, X_test, y_val, y_test = train_test_split(
    X_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp
)

print(f"Train rows:      {len(X_train)} ({len(X_train)/len(X_encoded):.1%})")
print(f"Validation rows: {len(X_val)} ({len(X_val)/len(X_encoded):.1%})")
print(f"Test rows:       {len(X_test)} ({len(X_test)/len(X_encoded):.1%})")

print("\nTraining RandomForestClassifier on the 70% TRAIN set...")
model = RandomForestClassifier(
    n_estimators=100,
    max_depth=8,
    min_samples_leaf=50,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1,
)
model.fit(X_train, y_train)

# ---------------------------------------------------------------------------
# 6. VALIDATE (15% validation set - used to check the model isn't overfitting
#    and to justify hyperparameter choices in your report; NOT used for training)
# ---------------------------------------------------------------------------
y_val_pred = model.predict(X_val)
y_val_proba = model.predict_proba(X_val)[:, 1]
print("\n--- VALIDATION SET Results (15%) ---")
print(classification_report(y_val, y_val_pred))
print(f"Validation ROC-AUC: {roc_auc_score(y_val, y_val_proba):.4f}")

# ---------------------------------------------------------------------------
# 7. FINAL TEST (15% test set - touched only once, for the final unbiased
#    number you report as your model's real-world performance)
# ---------------------------------------------------------------------------
y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

print("\n--- FINAL TEST SET Results (15%) ---")
print(classification_report(y_test, y_pred))
print(f"Test ROC-AUC: {roc_auc_score(y_test, y_proba):.4f}")

importances = pd.Series(model.feature_importances_, index=X_encoded.columns).sort_values(ascending=False)
print("\n--- Feature Importances ---")
print(importances)

# ---------------------------------------------------------------------------
# 7. SAVE MODEL + ENCODER + AIRPORT LOOKUP (needed at prediction time)
# ---------------------------------------------------------------------------
joblib.dump(model, os.path.join(OUTPUT_DIR, "delay_model.joblib"), compress=3)
joblib.dump(encoder, os.path.join(OUTPUT_DIR, "categorical_encoder.joblib"))
joblib.dump(categorical_features, os.path.join(OUTPUT_DIR, "categorical_features.joblib"))
joblib.dump(numeric_features, os.path.join(OUTPUT_DIR, "numeric_features.joblib"))

# Save lookup tables needed to build features for a NEW booking at prediction time
geo_lookup.to_csv(os.path.join(OUTPUT_DIR, "airport_geo_lookup.csv"))
route_stats = flights.groupby(["Dep_Airport", "Arr_Airport"])["is_delayed"].mean().rename("route_historical_delay_rate")
airline_stats = flights.groupby("Airline")["is_delayed"].mean().rename("airline_historical_delay_rate")
airport_stats = flights.groupby("Dep_Airport")["is_delayed"].mean().rename("dep_airport_historical_delay_rate")
route_stats.to_csv(os.path.join(OUTPUT_DIR, "route_historical_stats.csv"))
airline_stats.to_csv(os.path.join(OUTPUT_DIR, "airline_historical_stats.csv"))
airport_stats.to_csv(os.path.join(OUTPUT_DIR, "airport_historical_stats.csv"))

# Save recent weather per airport too (so we can look up "typical" weather for a future flight date)
weather_recent = weather.sort_values("time").groupby("airport_id").tail(1).set_index("airport_id")
weather_recent[weather_cols].to_csv(os.path.join(OUTPUT_DIR, "airport_weather_lookup.csv"))

print(f"\nModel and artifacts saved to '{OUTPUT_DIR}/' directory.")
print("Copy this whole folder into your Django project (e.g. ml/model_artifacts/).")
