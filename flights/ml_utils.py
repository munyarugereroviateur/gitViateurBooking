"""
SkyBook - Delay Prediction Utility (Django-side)
==================================================
Place this file in: flights/ml_utils.py

Matched to the real models:

class Aircraft(models.Model):
    model, registration_number, manufacturer, capacity,
    year_manufactured, last_maintenance

class Flight(models.Model):
    flight_number, airline, origin, destination,
    departure_time (DateTimeField), arrival_time, duration_minutes,
    aircraft (FK), capacity, price_per_seat, status, document
"""

import os
import datetime
import joblib
import pandas as pd
import numpy as np
from django.conf import settings

ARTIFACTS_DIR = os.path.join(settings.BASE_DIR, "ml_models", "model_artifacts")

_model = joblib.load(os.path.join(ARTIFACTS_DIR, "delay_model.joblib"))
_encoder = joblib.load(os.path.join(ARTIFACTS_DIR, "categorical_encoder.joblib"))
_categorical_features = joblib.load(os.path.join(ARTIFACTS_DIR, "categorical_features.joblib"))
_numeric_features = joblib.load(os.path.join(ARTIFACTS_DIR, "numeric_features.joblib"))

_geo_lookup = pd.read_csv(os.path.join(ARTIFACTS_DIR, "airport_geo_lookup.csv")).set_index("airport_code")
_route_stats = pd.read_csv(os.path.join(ARTIFACTS_DIR, "route_historical_stats.csv")).set_index(["Dep_Airport", "Arr_Airport"])
_airline_stats = pd.read_csv(os.path.join(ARTIFACTS_DIR, "airline_historical_stats.csv")).set_index("Airline")
_airport_stats = pd.read_csv(os.path.join(ARTIFACTS_DIR, "airport_historical_stats.csv")).set_index("Dep_Airport")
_weather_lookup = pd.read_csv(os.path.join(ARTIFACTS_DIR, "airport_weather_lookup.csv")).set_index("airport_id")

_GLOBAL_DELAY_RATE = _route_stats["route_historical_delay_rate"].mean()


def _haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def _time_of_day_label(dt: datetime.datetime) -> str:
    """Matches the buckets used in training: Morning/Afternoon/Evening/Night."""
    hour = dt.hour
    if 5 <= hour < 12:
        return "Morning"
    elif 12 <= hour < 17:
        return "Afternoon"
    elif 17 <= hour < 21:
        return "Evening"
    else:
        return "Night"


def predict_delay_probability(
    dep_airport: str,
    arr_airport: str,
    day_of_week: int,
    dep_time_label: str,
    airline: str,
    manufacturer: str,
    model_name: str,
    aircraft_age: int,
) -> float:
    """Core prediction function - returns probability between 0.0 and 1.0."""
    dep_airport = (dep_airport or "").upper()
    arr_airport = (arr_airport or "").upper()

    try:
        dep_lat, dep_lon = _geo_lookup.loc[dep_airport, ["LATITUDE", "LONGITUDE"]]
        arr_lat, arr_lon = _geo_lookup.loc[arr_airport, ["LATITUDE", "LONGITUDE"]]
        distance_km = _haversine(dep_lat, dep_lon, arr_lat, arr_lon)
    except KeyError:
        distance_km = 0.0

    if dep_airport in _weather_lookup.index:
        w = _weather_lookup.loc[dep_airport]
        tavg, tmin, tmax = w["tavg"], w["tmin"], w["tmax"]
        prcp, snow, wdir, wspd, pres = w["prcp"], w["snow"], w["wdir"], w["wspd"], w["pres"]
    else:
        tavg = tmin = tmax = prcp = snow = wdir = wspd = pres = 0.0

    route_rate = _route_stats["route_historical_delay_rate"].get((dep_airport, arr_airport), _GLOBAL_DELAY_RATE)
    airline_rate = _airline_stats["airline_historical_delay_rate"].get(airline, _GLOBAL_DELAY_RATE)
    airport_rate = _airport_stats["dep_airport_historical_delay_rate"].get(dep_airport, _GLOBAL_DELAY_RATE)

    row = {
        "Dep_Airport": dep_airport,
        "Arr_Airport": arr_airport,
        "DepTime_label": dep_time_label,
        "Airline": airline,
        "Manufacturer": manufacturer,
        "Model": model_name,
        "Day_Of_Week": day_of_week,
        "distance_km": distance_km,
        "Aicraft_age": aircraft_age,
        "tavg": tavg, "tmin": tmin, "tmax": tmax,
        "prcp": prcp, "snow": snow, "wdir": wdir, "wspd": wspd, "pres": pres,
        "route_historical_delay_rate": route_rate,
        "airline_historical_delay_rate": airline_rate,
        "dep_airport_historical_delay_rate": airport_rate,
    }
    X = pd.DataFrame([row])
    X_cat_encoded = _encoder.transform(X[_categorical_features])
    X_encoded = pd.DataFrame(X_cat_encoded, columns=_categorical_features)
    X_encoded[_numeric_features] = X[_numeric_features].values

    proba = _model.predict_proba(X_encoded)[0, 1]
    return round(float(proba), 4)


def predict_delay_probability_for_flight(flight) -> float:
    """
    Convenience wrapper: pass in a Flight model instance directly.
    Usage in views.py:
        flight.delay_probability = predict_delay_probability_for_flight(flight)
    """
    current_year = datetime.date.today().year
    aircraft_age = current_year - flight.aircraft.year_manufactured

    return predict_delay_probability(
        dep_airport=flight.origin,
        arr_airport=flight.destination,
        day_of_week=flight.departure_time.isoweekday(),
        dep_time_label=_time_of_day_label(flight.departure_time),
        airline=flight.airline,
        manufacturer=flight.aircraft.manufacturer,
        model_name=flight.aircraft.model,
        aircraft_age=aircraft_age,
    )
