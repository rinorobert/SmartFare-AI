# Auto Fare Transparency System - SmartFare-AI

## Problem Statement
Travelers in Kollam district often face uncertainty and disputes in last-mile auto and taxi fares due to non-usage of meters and arbitrary pricing. This project aims to build a data-driven system that estimates a fair fare range using Kerala government fare rules, distance, time, and real-world data to improve transparency and trust.

## Motivation
This project is inspired by common real-world experiences during last-mile travel from railway stations in Kollam, where passengers are often unsure whether the fare quoted by auto or taxi drivers is reasonable. The absence of transparent pricing frequently leads to discomfort and confusion for commuters, indicating a need for a simple, data-driven approach to estimate fair fares and improve trust in everyday travel.

## Milestones
- [x] Project scope and problem statement finalized
- [x] Environment setup
- [x] Data collection
- [x] Data analysis & preprocessing
- [x] ML model development
- [x] Backend API
- [x] Frontend application
- [ ] Deployment

## Project Scope
- Initial focus: Auto-rickshaws
- Area: Kollam district, Kerala
- Entry point: Railway stations
- Designed to be scalable to other regions and vehicle types (e.g., taxis)

## Development Setup
- Python 3.11
- Virtual environment (venv)
- Core dependencies managed using `requirements.txt`
- Structured project directories for data, modeling, API, and app layers

## Dataset
The project uses a small, manually curated dataset of last-mile auto-rickshaw trips from railway stations in Kollam district.  
Each record includes trip distance (validated using Google Maps), time of travel, government-expected fare calculated using official Kerala auto fare rules, and the actual fare charged.

The dataset is intentionally kept small and explainable at this stage to ensure correctness and transparency before applying data analysis and machine learning techniques.

## Data Analysis
Initial exploratory analysis was performed to understand pricing behavior and fare deviations.  
A fare deviation metric was derived by comparing actual fares with government-expected fares, and a binary `overcharged` label was introduced to identify cases where passengers paid more than the expected amount.  
Basic preprocessing steps were applied to ensure consistency and robustness for future data additions.

## Machine Learning
A simple regression model was developed to estimate typical real-world fare behavior based on trip distance and time of day.  
The model’s output is used alongside government fare rules to derive an overcharge risk indicator, improving transparency for users.

## Backend API

The backend of this project is built using **FastAPI** and serves as the core engine for fare transparency.  
It exposes a `/predict` endpoint where basic trip details such as distance and time of travel are provided as input.

Based on this input, the API returns:
- The **government-expected fare**, calculated using official fare rules  
- An **ML-estimated real-world fare**, reflecting typical charging behavior observed in practice  
- An **overcharge risk indicator**, which helps identify whether the quoted fare is unusually high  

The backend is intentionally designed to be simple, explainable, and modular, making it easy to integrate with a future **frontend interface or mobile application**.

## Frontend

The frontend is built using Streamlit, designed to be simple, visual, and easy to use for everyday commuters.

It allows users to:
- Enter trip distance and time of travel
- View government-expected fare and typical real-world fare
- Compare fares visually using charts
- Identify potential overcharging through clear risk indicators

---
## ▶️ How to Run the Project Locally

1️⃣ Start the Backend (FastAPI)
```bash
uvicorn api.main:app --reload
```

Backend will run at:
http://127.0.0.1:8000

2️⃣ Start the Frontend (Streamlit)
```bash
streamlit run frontend/app.py
```

Frontend will open at:
http://localhost:8501

⚠️ Make sure the backend is running before starting the frontend.

⚠️ Disclaimer
This tool is intended for informational and transparency purposes only.
Government fares are calculated strictly using official Kerala auto fare rules.
Real-world and quoted fares are estimates used to highlight pricing patterns and potential overcharging.

---

## About Me
I’m **Rino Robert**, a B.Tech student in **Artificial Intelligence & Data Science**, focused on building practical, end-to-end analytics projects aligned with real-world industry workflows.

📧 Email: rinorobert710@gmail.com  
🔗 LinkedIn: https://www.linkedin.com/in/rino-robert/