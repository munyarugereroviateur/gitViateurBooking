import joblib
from django.conf import settings

_model = None
_encoders = None


def _load():
    global _model, _encoders
    if _model is None:
        _model = joblib.load(settings.ML_MODEL_PATH)
        _encoders = joblib.load(settings.ML_ENCODERS_PATH)
    return _model, _encoders


def predict_delay_probability(flight):
    """Returns a delay probability (0-100) for a Flight instance."""
    model, encoders = _load()

    try:
        origin_enc = encoders['origin'].transform([flight.origin[:3].upper()])[0]
    except ValueError:
        origin_enc = 0

    try:
        dest_enc = encoders['destination'].transform([flight.destination[:3].upper()])[0]
    except ValueError:
        dest_enc = 0

    day_of_week = flight.departure_time.weekday()
    hour = flight.departure_time.hour
    aircraft_age = max(0, 2026 - flight.aircraft.year_manufactured)
    weather_severity = 2  # placeholder; replace with a live weather API call if available

    features = [[origin_enc, dest_enc, day_of_week, hour, aircraft_age, weather_severity]]
    probability = model.predict_proba(features)[0][1]
    return round(probability * 100, 1)