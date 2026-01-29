from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="SmartFare-AI API",
    description="Backend API for auto fare transparency using government rules and ML-based real-world fare estimation",
    version="0.1.0"
)


class FareRequest(BaseModel):
    distance_km: float
    time_of_day: str  # "day" or "night"


def predict_real_world_fare(distance_km: float, time_of_day: str) -> float:
    base_fare = 30
    per_km_rate = 15
    fare = base_fare + (distance_km * per_km_rate)

    if time_of_day.lower() == "night":
        fare *= 1.3

    return round(fare, 2)


def calculate_govt_fare(distance_km: float, time_of_day: str) -> float:
    minimum_km = 1.5
    minimum_fare = 30
    per_km_rate = 15

    if distance_km <= minimum_km:
        fare = minimum_fare
    else:
        fare = minimum_fare + (distance_km - minimum_km) * per_km_rate

    if time_of_day.lower() == "night":
        fare *= 1.5

    return round(fare, 2)


def overcharge_risk(actual: float, predicted: float) -> str:
    if actual <= predicted:
        return "Low"
    elif actual <= 1.2 * predicted:
        return "Medium"
    else:
        return "High"

@app.post("/predict")
def predict_fare(data: FareRequest):
    govt_fare = calculate_govt_fare(data.distance_km, data.time_of_day)
    predicted_fare = predict_real_world_fare(data.distance_km, data.time_of_day)

    # Simulated quoted fare for now
    quoted_fare = round(predicted_fare * 1.1, 2)

    risk = overcharge_risk(
        actual=quoted_fare,
        predicted=predicted_fare
    )

    return {
        "distance_km": data.distance_km,
        "time_of_day": data.time_of_day,
        "government_expected_fare": govt_fare,
        "ml_estimated_real_world_fare": predicted_fare,
        "simulated_quoted_fare": quoted_fare,
        "overcharge_risk": risk
    }

@app.get("/")
def root():
    return {"message": "SmartFare-AI backend is running"}