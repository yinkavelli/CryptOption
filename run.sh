#!/bin/bash
set -e

# Install deps if needed
pip install -r requirements.txt -q

# Launch app — opens at http://localhost:8501
streamlit run app.py
