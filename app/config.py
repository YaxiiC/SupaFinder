"""Configuration settings for PhD Supervisor Finder."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file for local development
load_dotenv()

# Try to import streamlit for secrets (only available in Streamlit Cloud)
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    st = None


def get_secret(key: str, default: str = "") -> str:
    """Get secret from Streamlit Secrets or environment variable.
    
    Priority:
    1. Streamlit Secrets (if running on Streamlit Cloud)
    2. Environment variable (for local development)
    """
    if STREAMLIT_AVAILABLE and st is not None:
        try:
            # Check if st.secrets exists and has the key
            if hasattr(st, 'secrets') and key in st.secrets:
                return st.secrets[key]
        except Exception:
            # If secrets not available, fall back to environment variable
            pass
    
    # Fall back to environment variable
    return os.getenv(key, default)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
CACHE_DB = PROJECT_ROOT / "cache.sqlite"

# DeepSeek API
DEEPSEEK_API_KEY = get_secret("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = get_secret("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = get_secret("DEEPSEEK_MODEL", "deepseek-chat")

# Search API - Google Custom Search Engine (CSE)
GOOGLE_CSE_KEY = get_secret("GOOGLE_CSE_KEY", "")
GOOGLE_CSE_CX = get_secret("GOOGLE_CSE_CX", "")
# Alternative search providers (not currently used)
BING_SEARCH_KEY = os.getenv("BING_SEARCH_KEY", "")

# Runtime settings
TARGET_SUPERVISORS = int(os.getenv("TARGET_SUPERVISORS", "100"))
MAX_SCHOOLS = int(os.getenv("MAX_SCHOOLS", "60"))
REQUESTS_PER_DOMAIN_PER_SEC = float(os.getenv("REQUESTS_PER_DOMAIN_PER_SEC", "1.0"))
CRAWL_MAX_DEPTH = int(os.getenv("CRAWL_MAX_DEPTH", "2"))
MAX_PAGES_PER_SCHOOL = int(os.getenv("MAX_PAGES_PER_SCHOOL", "30"))

# Scoring thresholds
# Core: High relevance (typically top 30-50% of scores)
# Adjacent: Medium relevance (lower scores, but still relevant)
CORE_THRESHOLD = 0.35  # Lowered from 0.5 to get more Core supervisors
ADJACENT_THRESHOLD = 0.2  # Lowered from 0.4 to catch more adjacent matches

# Directory page detection thresholds
# Minimum number of profile-like links to consider a page a directory (vs. personal profile)
DIRECTORY_MIN_PROFILE_LINKS = int(os.getenv("DIRECTORY_MIN_PROFILE_LINKS", "8"))
# Threshold for conservative directory detection (fewer links needed)
DIRECTORY_CONSERVATIVE_THRESHOLD = int(os.getenv("DIRECTORY_CONSERVATIVE_THRESHOLD", "5"))

# Text extraction thresholds
# Minimum text length to attempt extraction (lowered to allow short pages with structured data)
MIN_TEXT_LENGTH_FOR_EXTRACTION = int(os.getenv("MIN_TEXT_LENGTH_FOR_EXTRACTION", "20"))
# For profile URLs (like profiles.ucl.ac.uk), even shorter text is acceptable
MIN_TEXT_LENGTH_FOR_PROFILE_URL = int(os.getenv("MIN_TEXT_LENGTH_FOR_PROFILE_URL", "10"))

# Concurrency
MAX_CONCURRENT_REQUESTS = 5
REQUEST_TIMEOUT = 30

# Developer mode - unlimited access
# Set DEVELOPER_EMAILS to comma-separated list of developer emails
# Example: DEVELOPER_EMAILS=dev@example.com,admin@example.com
DEVELOPER_EMAILS = [e.strip().lower() for e in os.getenv("DEVELOPER_EMAILS", "").split(",") if e.strip()]

# Beta users - get free searches before requiring subscription
# Format: "email1@example.com:10,email2@example.com:10" (email:free_searches,email:free_searches)
# Each beta user gets the specified number of free searches (default: 10)
BETA_USERS_CONFIG = get_secret("BETA_USERS", "")
BETA_USERS = {}  # {email: free_searches_count}
if BETA_USERS_CONFIG:
    for entry in BETA_USERS_CONFIG.split(","):
        entry = entry.strip()
        if ":" in entry:
            email, count = entry.split(":", 1)
            email = email.strip().lower()
            try:
                count = int(count.strip())
                BETA_USERS[email] = count
            except ValueError:
                pass  # Skip invalid entries

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)

