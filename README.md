# SmartFare-AI – Auto Fare Transparency System

## Problem Statement
Travellers in Kollam district, especially during last-mile journeys from railway stations, often face confusion about auto and taxi fares. Meters are rarely used, and prices are usually quoted on the spot, which makes it difficult to know whether the fare is fair or not.

This project aims to build a simple, data-driven system that estimates fair fares using Kerala government rules along with real-world pricing patterns, helping improve transparency and trust for everyday commuters.

---

## Motivation
The idea for this project came from my own experiences while traveling from Kollam railway station to my home. Many times, I wasn’t sure whether the amount asked by the auto driver was reasonable, even though government fare rules exist.

This repeated uncertainty made me want to build a tool that could clearly show:
- What the government-expected fare should be
- What people are usually charged in real life
- Whether a quoted fare looks reasonable or not

---

## Milestones
- [x] Problem definition and scope
- [x] Data collection and preprocessing
- [x] Machine learning model
- [x] Backend API (FastAPI)
- [x] Frontend application (Streamlit)
- [x] Deployment

---

## 🌍 Live Demo
- **Frontend App**: https://smartfare-ai-mqpgtrah6ub96c2h3dugsc.streamlit.app/  
- **Backend API (Docs)**: https://smartfare-ai-backend.onrender.com/docs

---

## Project Scope
- Initial focus: Auto-rickshaws  
- Region: Kollam district, Kerala  
- Common entry point: Railway stations  
- Designed to scale to taxis and other regions in the future  

---

## Tech Stack
- Python 3.11  
- FastAPI (Backend)  
- Streamlit (Frontend)  
- Scikit-learn (ML)  
- Pandas, NumPy  
- Render & Streamlit Community Cloud (Deployment)

---

## Dataset
The dataset is small and manually created using real trip examples from Kollam railway stations.  
Each entry includes:
- Trip distance (verified using Google Maps)
- Time of travel (day/night)
- Government-expected fare (based on official rules)
- Actual fare charged

The dataset is intentionally kept small and simple to make the logic easy to understand and explain.

---

## Machine Learning Approach
A simple regression model is used to estimate typical real-world fare behavior based on distance and time of day.  
This ML estimate is not meant to replace government rules, but to reflect what usually happens in practice.

By comparing:
- Government fare  
- ML-estimated real-world fare  
- Quoted fare  

the system highlights a possible overcharge risk for users.

---

## Backend API
The backend is built using **FastAPI** and exposes a `/predict` endpoint.

For a given trip, the API returns:
- Government-expected fare
- ML-estimated real-world fare
- Overcharge risk indicator

The backend is kept modular and simple so it can be easily extended later.

---

## Frontend
The frontend is built using **Streamlit** with a focus on clarity and usability.

Users can:
- Enter trip distance and time of travel
- View a clear fare breakdown
- Compare fares visually using charts
- Understand overcharge risk through simple indicators and explanations

---

## ▶️ Run Locally

### Start Backend
```bash
uvicorn api.main:app --reload
```

Backend will run at:
http://127.0.0.1:8000

### Start Frontend
```bash
streamlit run frontend/app.py
```

Frontend will open at:
http://localhost:8501

⚠️ Make sure the backend is running before starting the frontend.

## ⚠️ Disclaimer
This tool is intended for informational and transparency purposes only.
Government fares are calculated strictly using official Kerala auto fare rules.
Real-world and quoted fares are estimates used to highlight pricing patterns and potential overcharging.

---

## Future Enhancements
This project is intentionally kept simple in its first version. Possible future improvements include:
- Support for waiting time and return journey charges
- Map-based distance calculation instead of manual input
- Taxi fare support alongside auto-rickshaws
- Weather or time-based fare analysis
- Improved ML models using a larger real-world dataset
- Explainable AI (XAI) features to show how fare estimates are derived

---

## About Me
I’m **Rino Robert**, a B.Tech student in **Artificial Intelligence & Data Science**, focused on building practical, end-to-end analytics projects aligned with real-world industry workflows.

📧 Email: rinorobert710@gmail.com  
🔗 LinkedIn: https://www.linkedin.com/in/rino-robert/