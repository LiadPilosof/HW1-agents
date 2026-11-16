import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load environment variables (.env) - mirroring reference notebooks convention
load_dotenv(PROJECT_ROOT / ".env", override=True)

# Data paths
DATA_DIR = PROJECT_ROOT / "data"
LINKEDIN_PROFILE_PATH = DATA_DIR / "linkedin_profile.txt"
PERSONAL_SUMMARY_PATH = DATA_DIR / "personal_summary.txt"

# Logs paths
LOGS_DIR = PROJECT_ROOT / "logs"
INSPECTION_LOG_PATH = LOGS_DIR / "inspection_log.json"

# Model configuration
DEFAULT_MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
CRITIC_MODEL_NAME = os.getenv("CRITIC_MODEL_NAME", DEFAULT_MODEL_NAME)


def load_file_content(path: Path) -> str:
    """Read and return content of a text file using utf-8 encoding."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def get_linkedin_profile() -> str:
    """Load the LinkedIn profile background text."""
    return load_file_content(LINKEDIN_PROFILE_PATH)


def get_personal_summary() -> str:
    """Load the personal summary background text."""
    return load_file_content(PERSONAL_SUMMARY_PATH)


def get_openai_client(api_key: Optional[str] = None) -> OpenAI:
    """
    Initialize and return the OpenAI API client.
    Supports OPENAI_API_KEY and optional OPENAI_BASE_URL.
    Raises ValueError with a clear explanation if OPENAI_API_KEY is not set.
    """
    key = api_key or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")

    if not key or key.strip() == "your_openai_api_key_here":
        raise ValueError(
            "OPENAI_API_KEY אינו מוגדר. אנא הגדר את המפתח בקובץ .env (ראה דוגמה ב-.env.example)."
        )

    # Mirroring reference notebook pattern
    if base_url:
        return OpenAI(api_key=key, base_url=base_url)
    return OpenAI(api_key=key)
