"""Project-local configuration, reloaded on each Streamlit run."""

import os
from pathlib import Path

from dotenv import dotenv_values


PROJECT_DIR = Path(__file__).resolve().parent
ENV_FILE = PROJECT_DIR / ".env"
MODEL = "gpt-6.1-sol"
REASONING_LEVELS = ("low", "medium", "high", "xhigh", "max")
DEFAULT_REASONING = "medium"


def get_api_key():
    """Prefer the saved project key; allow deployment environment credentials."""
    saved_key = dotenv_values(ENV_FILE, encoding="utf-8-sig").get("OPENAI_API_KEY") or ""
    return saved_key.strip() or os.environ.get("OPENAI_API_KEY", "").strip()
