from fastapi import FastAPI
from pydantic import BaseModel
import math

app = FastAPI(
    title="SmartFare-AI API",
    description="Backend API for auto fare transparency using government rules and ML-based real-world fare estimation",
    version="0.1.0"
)


class FareRequest(BaseModel):
    distance_km: float
    time_of_day: str
    quoted_fare: float
    waiting_minutes: int = 0
    return_journey: bool = False
    major_city: bool = True


def predict_real_world_fare(distance_km: float, time_of_day: str) -> float:
    base_fare = 30
    per_km_rate = 15
    fare = base_fare + (distance_km * per_km_rate)

    if time_of_day.lower() == "night":
        fare *= 1.3

    return round(fare, 2)

def calculate_govt_fare_breakdown(
    distance_km: float,
    time_of_day: str,
    waiting_minutes: int,
    return_journey: bool,
    major_city: bool
):
    minimum_km = 1.5
    minimum_fare = 30
    per_km_rate = 15

    # Minimum fare + distance charge
    if distance_km <= minimum_km:
        distance_charge = 0
        fare = minimum_fare
    else:
        distance_charge = (distance_km - minimum_km) * per_km_rate
        fare = minimum_fare + distance_charge

    # Waiting charge
    waiting_charge = math.ceil(waiting_minutes / 15) * 10 if waiting_minutes > 0 else 0
    fare += waiting_charge

    # Return journey charge
    return_charge = 0
    if return_journey and not major_city:
        return_charge = fare * 0.5
        fare += return_charge

    # Night surcharge
    night_charge = 0
    if time_of_day.lower() == "night":
        night_charge = fare * 0.5
        fare += night_charge

    return {
        "minimum_fare": round(minimum_fare, 2),
        "distance_charge": round(distance_charge, 2),
        "waiting_charge": round(waiting_charge, 2),
        "return_charge": round(return_charge, 2),
        "night_charge": round(night_charge, 2),
        "government_expected_fare": round(fare, 2)
    }


def overcharge_risk(actual: float, predicted: float) -> str:
    if actual <= predicted:
        return "Low"
    elif actual <= 1.2 * predicted:
        return "Medium"
    else:
        return "High"

@app.post("/predict")
def predict_fare(data: FareRequest):
    fare_breakdown = calculate_govt_fare_breakdown(
        data.distance_km,
        data.time_of_day,
        data.waiting_minutes,
        data.return_journey,
        data.major_city
    )

    total_govt_fare = fare_breakdown["government_expected_fare"]
    predicted_fare = predict_real_world_fare(data.distance_km, data.time_of_day)

    risk = overcharge_risk(
        actual=data.quoted_fare,
        predicted=predicted_fare
    )

    return {
        "distance_km": data.distance_km,
        "time_of_day": data.time_of_day,

        "government_expected_fare": total_govt_fare,

        "minimum_fare": fare_breakdown["minimum_fare"],
        "distance_charge": fare_breakdown["distance_charge"],
        "waiting_charge": fare_breakdown["waiting_charge"],
        "return_charge": fare_breakdown["return_charge"],
        "night_charge": fare_breakdown["night_charge"],

        "ml_estimated_real_world_fare": predicted_fare,

        "quoted_fare": data.quoted_fare,

        "overcharge_risk": risk,

        "return_journey": data.return_journey,
        "major_city": data.major_city
    }

@app.get("/")
def root():
    return {"message": "SmartFare-AI backend is running"}