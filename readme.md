# 🚦 FlowGuard AI – Intelligent Event Congestion Management System

## Overview

FlowGuard AI is an AI-powered event congestion management platform designed to assist traffic authorities, event organizers, and city administrators in predicting congestion levels, estimating event impact, and optimizing traffic resource allocation.

The system leverages historical event data, machine learning models, congestion analytics, and dynamic officer deployment recommendations to improve traffic flow and reduce congestion caused by public events.

---

## Problem Statement

Large public events such as:

- Religious Gatherings
- Political Rallies
- Concerts
- Marathons
- Festivals
- Sports Events

often cause severe traffic congestion due to sudden increases in vehicle and pedestrian movement.

Traditional planning methods rely heavily on manual estimation, which can result in:

- Traffic Bottlenecks
- Insufficient Police Deployment
- Delayed Emergency Response
- Increased Travel Time
- Public Inconvenience

FlowGuard AI addresses these challenges through data-driven decision making.

---

## ✨ Features

### 📅 Event Planner

Plan and simulate upcoming events by specifying:

- Event Type
- Event Location
- Start and End Points
- Date and Time
- Road Closure Requirements
- Expected Crowd Size

---

### 📊 Congestion Risk Assessment

Calculates congestion risk using:

- Historical Event Patterns
- Location-Specific Traffic Trends
- Time-of-Day Analysis
- Day-of-Week Analysis
- Event Category Characteristics

Outputs a numerical congestion score.

---

### ⏱ Event Duration Prediction

Machine Learning model predicts:

- Expected Event Duration
- Potential Congestion Window
- Traffic Impact Period

based on historical event records.

---

### 👮 Officer Allocation Recommendation

Recommends required traffic personnel using:

- Event Type
- Historical Deployment Records
- Junction Congestion Statistics
- Predicted Traffic Load

Outputs:

- Recommended Officers
- Traffic Management Requirements
- Resource Allocation Insights

---

### 📍 Junction Impact Analysis

Analyzes nearby traffic junctions and estimates:

- Congestion Probability
- Junction Risk Score
- Traffic Pressure Levels

---

### 🔄 Self-Learning Feedback System

Supports post-event feedback collection:

- Actual Congestion Observed
- Actual Officers Deployed
- Actual Event Duration

The system updates its internal knowledge using feedback-driven learning to improve future recommendations.

---

### 📈 Event Reports

Generate detailed event reports including:

- Predicted Metrics
- Actual Metrics
- Resource Utilization
- Congestion Analysis
- Planning Recommendations

---

## 🛠 Tech Stack

### Frontend
- Streamlit

### Backend
- Python

### Data Processing
- Pandas
- NumPy

### Machine Learning
- Scikit-learn
- Joblib

### Visualization
- Plotly
- Folium
- Streamlit-Folium

### Geospatial Analysis
- Latitude & Longitude Based Calculations
- Distance Estimation
- Junction Mapping

---

## 📂 Project Structure

```text
FlowGuard-AI/
│
├── app.py
│
├── pages/
│   ├── Event_Planner.py
│   ├── Event_Report.py
│   ├── Analytics.py
│   └── Feedback.py
│
├── models/
│   ├── duration_model.pkl
│   └── officer_model.pkl
│
├── data/
│   ├── events.csv
│   ├── junctions.csv
│   └── traffic_history.csv
│
├── utils/
│   ├── prediction.py
│   ├── congestion.py
│   ├── officer_allocation.py
│   └── self_learning.py
│
├── assets/
│
├── requirements.txt
│
└── README.md
```

---

## 🤖 Machine Learning Components

### Event Duration Prediction Model

Predicts:

- Estimated Event Duration
- Congestion Window

using:

- Event Type
- Day Type (Weekday / Weekend)
- Start Hour
- Historical Event Patterns
- Location Statistics

---

### Officer Requirement Estimation

Predicts:

- Required Traffic Officers

using:

- Event Characteristics
- Congestion Scores
- Historical Deployments
- Junction Load Statistics

---

## 📊 Dataset Features

Sample attributes used:

```text
event_type
latitude
longitude
endlatitude
endlongitude
address
end_address
event_cause
requires_road_closure
start_datetime
end_datetime
police_station
```

Additional engineered features:

- Event Duration
- Day Type
- Hour of Day
- Junction Statistics
- Historical Congestion Indicators

---

## 🚀 Installation

### Clone Repository

```bash
git clone https://github.com/your-username/FlowGuard-AI.git

cd FlowGuard-AI
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Application

```bash
streamlit run app.py
```

---

## 🌐 Deployment

The application is deployed using Streamlit Community Cloud.

Any updates pushed to the `main` branch are automatically redeployed.

---

## 🔮 Future Enhancements

- Real-Time Traffic API Integration
- Emergency Vehicle Route Prioritization
- Reinforcement Learning Based Resource Allocation
- Live Congestion Heatmaps
- Weather-Aware Congestion Prediction
- Multi-City Deployment Support
- Predictive Traffic Rerouting

---

## 🎯 Impact

FlowGuard AI helps authorities:

- Reduce traffic congestion
- Improve event planning
- Optimize officer deployment
- Enhance public safety
- Improve emergency response readiness

---

## 👨‍💻 Team

Developed as part of an AI-powered Smart Traffic and Event Congestion Management project.

### Built With

- Python
- Streamlit
- Machine Learning
- Data Analytics
- Geospatial Intelligence

---

## 📜 License

This project is intended for academic, research, and demonstration purposes.