# AI-Powered Community Health Worker (CHW) E-Learning Platform

A bilingual (English/Kinyarwanda) prototype for CHW e-learning, demonstrating 4 AI capabilities:

- **AI-Powered Grading System** (NLP, semantic similarity, feedback)
- **Intelligent Course Content Management** (summarization, diagram prompts, Q&A, adaptation)
- **Personalized Recommendation System** (geo/symptom-based, adaptive paths)
- **Analytics Dashboard & Data Visualization** (engagement, progress, regional compare, predictive)

## Features
- Streamlit dashboard (offline, simulated data)
- FastAPI endpoints (mirroring Streamlit features)
- Modular, testable Python code
- Bilingual (EN/KI) support
- No heavy dependencies by default

## Quickstart

1. **Install requirements:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Generate synthetic data:**
   ```bash
   python generate_synthetic_data.py
   ```
3. **Run Streamlit demo:**
   ```bash
   streamlit run app/streamlit_app.py
   ```
4. **Run FastAPI server:**
   ```bash
   uvicorn api.main:app --reload
   ```

## Project Structure
- `app/streamlit_app.py` — Streamlit dashboard
- `api/main.py` — FastAPI app
- `src/models/` — Core logic (grading, content, recommend, analytics)
- `data/` — Simulated data
- `tests/` — Unit tests

## Requirements
- Python 3.10+
- Streamlit, FastAPI, scikit-learn, numpy, pandas, (optional: sentence-transformers)

## Notes
- All features run offline with simulated data.
- Heavy models are optional; code falls back to light methods if unavailable.
- See code comments and docstrings for extension points.
