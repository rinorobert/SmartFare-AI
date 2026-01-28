# Auto Fare Transparency System - SmartFare-AI

## Problem Statement
Travelers in Kollam district often face uncertainty and disputes in last-mile auto and taxi fares due to non-usage of meters and arbitrary pricing. This project aims to build a data-driven system that estimates a fair fare range using Kerala government fare rules, distance, time, and real-world data to improve transparency and trust.

## Motivation
This project is inspired by common real-world experiences during last-mile travel from railway stations in Kollam, where passengers are often unsure whether the fare quoted by auto or taxi drivers is reasonable. The absence of transparent pricing frequently leads to discomfort and confusion for commuters, indicating a need for a simple, data-driven approach to estimate fair fares and improve trust in everyday travel.

## Milestones
- [x] Project scope and problem statement finalized
- [x] Environment setup
- [x] Data collection
- [ ] Data analysis & preprocessing
- [ ] ML model development
- [ ] Backend API
- [ ] Frontend application
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

## About Me
I’m **Rino Robert**, a B.Tech student in **Artificial Intelligence & Data Science**, focused on building practical, end-to-end analytics projects aligned with real-world industry workflows.

📧 Email: rinorobert710@gmail.com  
🔗 LinkedIn: https://www.linkedin.com/in/rino-robert/