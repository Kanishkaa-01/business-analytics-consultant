<div align="center">

# Business Analytics Consultant
### Explainable Business Decision Intelligence System

*Transforming structured business data into explainable, evidence-backed insights for confident decision-making.*

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-Frontend-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-Typed-3178C6?logo=typescript&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-4169E1?logo=postgresql&logoColor=white)

</div>

---

## Overview
 
**Business Analytics Consultant** is a web-based analytics and decision-support platform that converts raw, structured business datasets into **meaningful, explainable, and actionable insights**.
 
It brings together exploratory data analysis, data quality auditing, statistical diagnostics, and predictive analytics into a single, connected workflow helping users understand business performance, surface risks and opportunities, and make informed decisions backed by evidence rather than intuition.

It provides an integrated analytical workflow that connects raw business data with evidence-based findings, prioritized recommendations and scenario-based decision support.

## Key Features

### 1. Data Ingestion & Dataset Profiling
- Upload and process structured business datasets.
- Identify dataset dimensions, column names and data types.
- Detect numerical, categorical and date-related attributes.
- Generate dataset profiles and calculate file integrity hashes.

### 2. Data Quality Assessment
- Evaluate data completeness, validity, uniqueness and consistency.
- Identify missing values, duplicate records and potential outliers.
- Apply statistical techniques for data quality evaluation.
- Generate data quality scores and reliability indicators.

### 3. Exploratory Data Analysis (EDA)
- Perform descriptive statistical analysis.
- Examine data distributions, variability and skewness.
- Identify trends, patterns and unusual observations.
- Explore relationships between business variables.

### 4. Business Performance Analytics
- Calculate and monitor Key Performance Indicators (KPIs).
- Generate business health scores.
- Compare current and baseline business performance.
- Analyse performance across different business segments.

### 5. Diagnostic & Root-Cause Analysis
- Identify significant business performance variations.
- Perform segment-level contribution analysis.
- Apply statistical techniques to investigate potential contributing factors.
- Generate explainable analytical findings.

### 6. Risk & Opportunity Analysis
- Identify potential business risks and performance deterioration.
- Analyse business concentration and financial exposure.
- Highlight opportunities for operational and financial improvement.
- Generate early-warning indicators based on configured thresholds.

### 7. Evidence-Based Analysis
- Connect analytical findings with supporting dataset information.
- Maintain traceability between observations and analytical results.
- Present supporting evidence to improve transparency and verifiability.

### 8. Recommendation Prioritization
- Generate recommendations based on analytical findings.
- Evaluate potential actions using impact, confidence and ease criteria.
- Prioritize recommendations according to defined scoring rules.
- Present actionable insights to support business planning.

### 9. Predictive Analytics & Decision Support
- Analyse historical business trends for forecasting.
- Perform what-if scenario analysis to evaluate hypothetical business changes.
- Compare potential business outcomes under defined assumptions.
- Support strategic planning through predictive insights.

### 10. Visualization & Reporting
- Generate interactive business dashboards and visualizations.
- Present KPIs, analytical findings and performance comparisons.
- Generate business reports to communicate insights and recommendations.

## Technology Stack

| Category | Technologies |
|---|---|
| Programming Languages | Python, TypeScript |
| Frontend | React.js, Vite |
| UI Framework | Tailwind CSS |
| Backend | FastAPI |
| Data Analysis | Pandas, NumPy |
| Data Visualization | Apache ECharts |
| Database | PostgreSQL, SQLite |
| ORM | SQLAlchemy |
| Development Tools | VS Code, Git, GitHub |

## System Workflow
 
The platform follows a structured, nine-stage analytical pipeline:
 
| Stage | Description |
|---|---|
| 1. Data Setup & Immutability | Upload datasets, identify business metrics, establish data integrity |
| 2. Data Quality & Reliability Audit | Evaluate data quality and flag potential issues |
| 3. Business Health Assessment | Calculate KPIs and assess overall performance |
| 4. Business Diagnosis | Analyze performance variation and segment-level contribution |
| 5. Root-Cause Investigation | Examine statistical relationships and contributing factors |
| 6. Risk & Opportunity Identification | Identify threats and improvement opportunities |
| 7. Evidence Chains | Link findings to supporting data and calculations |
| 8. Recommendations & Action Matrix | Prioritize potential business actions |
| 9. Decision Support & What-If Simulation | Evaluate scenarios to support strategic decisions |
 
---

## Analytical Techniques

The system incorporates various data analysis and statistical techniques, including:

- Exploratory Data Analysis (EDA)
- Descriptive Statistics
- Interquartile Range (IQR) for Outlier Detection
- Data Quality Metrics
- Variance Analysis
- Segment-Level Performance Analysis
- Correlation and Regression Analysis
- Analysis of Variance (ANOVA)
- Pareto Analysis
- Herfindahl-Hirschman Index (HHI)
- Forecasting Evaluation Metrics
- Impact-Based Recommendation Prioritization

## Project Architecture
 
The application follows a **frontend–backend architecture**:
 
The application follows a decoupled **frontend–backend architecture**:
 
**Frontend** — React.js, TypeScript, Vite
- Interactive dashboards and analytical components
- Data visualization and reporting interfaces
- REST API integration with the backend

**Backend** — Python, FastAPI
- Dataset ingestion and profiling
- Data quality and statistical analysis engines
- Business diagnosis and recommendation modules
- Forecasting and scenario analysis services

**Database** — SQLAlchemy ORM
- PostgreSQL as the primary database
- SQLite as a lightweight fallback

---

## Installation & Setup

### Prerequisites

Ensure the following are installed:

- Python 3.10 or later (subject to project dependencies)
- Node.js and npm
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/Kanishkaa-01/business-analytics-consultant.git
```

```bash
cd business-analytics-consultant
```

### 2. Backend Setup

Navigate to the backend directory:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate the environment on Windows:

```powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the FastAPI server:

```bash
uvicorn app.main:app --reload --port 8001
```

Backend API documentation:

```text
http://127.0.0.1:8001/docs
```

### 3. Frontend Setup

Open a new terminal and navigate to the frontend directory:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

Open the local URL displayed in the terminal, typically:

```text
http://localhost:5173
```

## Research Contribution

The project explores an integrated approach to business decision support by connecting data quality assessment, exploratory analysis, statistical diagnosis, evidence traceability and recommendation prioritization.

Its primary focus is to bridge the gap between conventional business reporting and explainable decision-making by making analytical findings more transparent, traceable and actionable.

## Future Scope

Potential enhancements include:

- Natural language querying for business analytics.
- Advanced forecasting and predictive modelling.
- Expanded business document intelligence.
- Enhanced recommendation and optimization techniques.
- Real-time business performance monitoring.
- Advanced scenario comparison and simulation.
- Cloud deployment and collaborative decision support.

## Author

**Kanishkaa S.**

MSc Information Technology Student

[GitHub](https://github.com/Kanishkaa-01)

---

