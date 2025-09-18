"""
Configuration settings for the USV Investment Research Tool
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Parallel.ai API configuration
PARALLEL_API_KEY = os.getenv("PARALLEL_API_KEY", "")
BASE_URL = "https://api.parallel.ai"

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Default settings
DEFAULT_RESULT_LIMIT = 10
MAX_RESULT_LIMIT = 100
MIN_RESULT_LIMIT = 1
