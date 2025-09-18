"""
Configuration settings for the USV Investment Research Tool
"""
import streamlit as st

# Parallel.ai API configuration
try:
    PARALLEL_API_KEY = st.secrets["parallel_api_key"]
except (KeyError, AttributeError):
    PARALLEL_API_KEY = ""

BASE_URL = "https://api.parallel.ai"

# OpenRouter configuration
try:
    OPENROUTER_API_KEY = st.secrets["openrouter_api_key"]
except (KeyError, AttributeError):
    OPENROUTER_API_KEY = ""

# Default settings
DEFAULT_RESULT_LIMIT = 10
MAX_RESULT_LIMIT = 100
MIN_RESULT_LIMIT = 1
