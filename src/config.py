"""Project paths, model names, background-source loading and the OpenAI client factory."""

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env", override=True)

DATA_DIR = PROJECT_ROOT / "data"
LINKEDIN_PROFILE_PATH = DATA_DIR / "linkedin_profile.txt"
PERSONAL_SUMMARY_PATH = DATA_DIR / "personal_summary.txt"

INSPECTION_LOG_PATH = PROJECT_ROOT / "logs" / "inspection_log.json"

# The Actor and the Critic use separate calls and prompts; they may share a model.
ACTOR_MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
CRITIC_MODEL_NAME = os.getenv("CRITIC_MODEL_NAME", ACTOR_MODEL_NAME)

_API_KEY_PLACEHOLDER = "your_openai_api_key_here"


def load_file_content(path: Path) -> str:
    """Read a UTF-8 text file and return its stripped content."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def get_linkedin_profile() -> str:
    """Load the LinkedIn profile background source."""
    return load_file_content(LINKEDIN_PROFILE_PATH)


def get_personal_summary() -> str:
    """Load the personal summary background source."""
    return load_file_content(PERSONAL_SUMMARY_PATH)


def get_openai_client() -> OpenAI:
    """
    Build the OpenAI client from OPENAI_API_KEY (and optional OPENAI_BASE_URL).

    Raises ValueError with a clear Hebrew message if the key is missing.
    """
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key or key == _API_KEY_PLACEHOLDER:
        raise ValueError(
            "OPENAI_API_KEY אינו מוגדר. הגדירו את המפתח בקובץ .env (ראו דוגמה ב-.env.example)."
        )
    return OpenAI(api_key=key, base_url=os.getenv("OPENAI_BASE_URL") or None)
