from fastapi import FastAPI
from pydantic import BaseModel
import math, os, json
import joblib
import pandas as pd

app = FastAPI(
    title="SmartFare-AI API",
    description="Kerala auto fare transparency — government rules + empirical fare model.",
    version="0.2.0"
)

_BASE         = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH    = os.path.join(_BASE, "model", "fare_model.pkl")
FEATURES_PATH = os.path.join(_BASE, "model", "features.json")

_model    = None
_features = None


def get_model():
    global _model, _features
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model not found: {MODEL_PATH}")
        _model = joblib.load(MODEL_PATH)
        with open(FEATURES_PATH) as f:
            _features = json.load(f)
    return _model, _features


def _base_govt_fare(distance_km: float) -> float:
    """Govt fare without surcharges — used as ML feature."""
    mf, mkm, pkm = 30.0, 1.5, 15.0
    fare = mf if distance_km <= mkm else mf + (distance_km - mkm) * pkm
    return fare + (fare - mf) * 0.5


def _fallback_typical_fare(distance_km: float, time_of_day: str) -> float:
    """
    Rule-based typical fare when model unavailable.
    Derived from real Kerala auto observations:
      <=1.5 km  day  -> 40
      <=1.5 km  night-> 50
      >1.5 km   day  -> ceil(govt/10)*10 + 20
      >1.5 km   night-> ceil(govt/10)*10 + 40
    """
    gf = _base_govt_fare(distance_km)
    if distance_km <= 1.5:
        return 50.0 if time_of_day.lower() == "night" else 40.0
    rounded = math.ceil(gf / 10) * 10
    markup  = 40 if time_of_day.lower() == "night" else 20
    return float(rounded + markup)


class FareRequest(BaseModel):
    distance_km:     float
    time_of_day:     str
    quoted_fare:     float
    waiting_minutes: int  = 0
    return_journey:  bool = False
    major_city:      bool = True


def calc_govt_fare_breakdown(
    distance_km:     float,
    time_of_day:     str,
    waiting_minutes: int,
    return_journey:  bool,
    major_city:      bool,
):
    minimum_km, minimum_fare, per_km_rate = 1.5, 30.0, 15.0

    if distance_km <= minimum_km:
        distance_charge = 0.0
        fare = minimum_fare
    else:
        distance_charge = (distance_km - minimum_km) * per_km_rate
        fare = minimum_fare + distance_charge

    waiting_charge = math.ceil(waiting_minutes / 15) * 10 if waiting_minutes > 0 else 0.0
    fare += waiting_charge

    return_charge = 0.0
    if not return_journey and not major_city:
        return_charge = (fare - minimum_fare) * 0.5
        fare += return_charge

    night_charge = 0.0
    if time_of_day.lower() == "night":
        night_charge = fare * 0.5
        fare += night_charge

    return {
        "minimum_fare":             round(minimum_fare,    2),
        "distance_charge":          round(distance_charge, 2),
        "waiting_charge":           round(waiting_charge,  2),
        "return_charge":            round(return_charge,   2),
        "night_charge":             round(night_charge,    2),
        "government_expected_fare": round(fare,            2),
    }


def predict_typical_fare(distance_km: float, time_of_day: str) -> float:
    """
    Predict typical fare using trained model.
    Always falls back to empirical estimate if model unavailable —
    never returns 0.
    """
    try:
        model, features = get_model()
        gf       = _base_govt_fare(distance_km)
        is_night = 1 if time_of_day.lower() == "night" else 0
        X = pd.DataFrame([{
            "distance_km":  distance_km,
            "is_night":     is_night,
            "govt_fare":    gf,
            "night_x_dist": is_night * distance_km,
        }])[features]
        pred = model.predict(X)[0]
        result = round(float(pred), 2)
        # Sanity check — never return 0 or negative
        if result <= 0:
            return _fallback_typical_fare(distance_km, time_of_day)
        return result
    except Exception:
        # Model not deployed yet or any failure — use empirical fallback
        return _fallback_typical_fare(distance_km, time_of_day)


def overcharge_risk(quoted: float, typical: float) -> str:
    if quoted <= typical:
        return "Low"
    elif quoted <= 1.2 * typical:
        return "Medium"
    else:
        return "High"


@app.post("/predict")
def predict_fare(data: FareRequest):
    breakdown    = calc_govt_fare_breakdown(
        data.distance_km, data.time_of_day,
        data.waiting_minutes, data.return_journey, data.major_city
    )
    typical_fare = predict_typical_fare(data.distance_km, data.time_of_day)
    risk         = overcharge_risk(data.quoted_fare, typical_fare)

    return {
        "distance_km":              data.distance_km,
        "time_of_day":              data.time_of_day,
        "government_expected_fare": breakdown["government_expected_fare"],
        "minimum_fare":             breakdown["minimum_fare"],
        "distance_charge":          breakdown["distance_charge"],
        "waiting_charge":           breakdown["waiting_charge"],
        "return_charge":            breakdown["return_charge"],
        "night_charge":             breakdown["night_charge"],
        "typical_fare":             typical_fare,
        "quoted_fare":              data.quoted_fare,
        "overcharge_risk":          risk,
        "return_journey":           data.return_journey,
        "major_city":               data.major_city,
    }


@app.get("/")
def root():
    return {"message": "SmartFare-AI backend is running"}