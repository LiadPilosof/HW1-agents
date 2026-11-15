"""
Automated verification tests for Part A components:
- Background sources loading
- System prompt construction & constraints
- Inspection log creation and serialization
- History normalization
- Message construction for LLM Actor
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.actor import Actor, normalize_history
from src.config import (
    DATA_DIR,
    INSPECTION_LOG_PATH,
    LINKEDIN_PROFILE_PATH,
    PERSONAL_SUMMARY_PATH,
    get_linkedin_profile,
    get_personal_summary,
)
from src.logger import InspectionLogger
from src.prompts import build_system_prompt


def test_background_sources():
    """Verify that both background source files exist, are non-empty, and contain profile disclaimers."""
    assert LINKEDIN_PROFILE_PATH.exists(), "linkedin_profile.txt is missing"
    assert PERSONAL_SUMMARY_PATH.exists(), "personal_summary.txt is missing"

    linkedin_text = get_linkedin_profile()
    summary_text = get_personal_summary()

    assert len(linkedin_text) > 200, "linkedin_profile.txt is too short"
    assert len(summary_text) > 100, "personal_summary.txt is too short"

    # Verify sample profile disclaimer
    assert "פרופיל לדוגמה" in linkedin_text, "Missing 'פרופיל לדוגמה' in linkedin_profile.txt"
    assert "פרופיל לדוגמה" in summary_text, "Missing 'פרופיל לדוגמה' in personal_summary.txt"

    # Verify key sections
    for keyword in ["השכלה", "ניסיון תעסוקתי", "פרויקטים", "מיומנויות"]:
        assert keyword in linkedin_text, f"Missing section '{keyword}' in linkedin_profile.txt"

    print("✓ test_background_sources passed")


def test_system_prompt():
    """Verify system prompt structure and rule constraints."""
    summary_text = get_personal_summary()
    linkedin_text = get_linkedin_profile()
    prompt = build_system_prompt(summary_text, linkedin_text)

    # Verify embedded text
    assert summary_text in prompt, "Personal summary not embedded in system prompt"
    assert linkedin_text in prompt, "LinkedIn profile not embedded in system prompt"

    # Verify key prompt rules
    assert "ביסוס קפדני במקורות" in prompt, "Strict Grounding rule missing from prompt"
    assert "טיפול במידע חסר" in prompt, "Missing Information rule missing from prompt"
    assert "אינו קיים" in prompt or "אינו מופיע" in prompt, "Explicit absence instruction missing"
    assert "עברית" in prompt, "Hebrew language instruction missing"

    print("✓ test_system_prompt passed")


def test_history_normalization():
    """Verify history normalization for both Gradio formats."""
    # Format 1: List of dicts (Gradio 4/5 messages)
    history_dicts = [
        {"role": "user", "content": "שלום"},
        {"role": "assistant", "content": "שלום! איך אוכל לעזור?"},
    ]
    norm1 = normalize_history(history_dicts)
    assert norm1 == history_dicts, "Failed to normalize list of dicts"

    # Format 2: List of tuples/pairs (Legacy Gradio)
    history_tuples = [
        ["שלום", "שלום! איך אוכל לעזור?"],
        ["מה שמך?", "שמי אלון ברק."],
    ]
    norm2 = normalize_history(history_tuples)
    assert len(norm2) == 4, f"Expected 4 messages, got {len(norm2)}"
    assert norm2[0] == {"role": "user", "content": "שלום"}
    assert norm2[1] == {"role": "assistant", "content": "שלום! איך אוכל לעזור?"}
    assert norm2[2] == {"role": "user", "content": "מה שמך?"}
    assert norm2[3] == {"role": "assistant", "content": "שמי אלון ברק."}

    print("✓ test_history_normalization passed")


def test_inspection_logger(tmp_path: Path = None):
    """Verify logging turns to inspection_log.json."""
    test_log_path = Path("/tmp/test_inspection_log.json")
    if test_log_path.exists():
        test_log_path.unlink()

    logger = InspectionLogger(log_path=test_log_path)
    entry = logger.log_turn(
        user_message="מה שמך?",
        candidate_response="שמי אלון ברק.",
        final_response="שמי אלון ברק.",
        status="APPROVED",
        session_id="test_session_1",
        turn_index=1,
    )

    assert entry["user_message"] == "מה שמך?"
    assert entry["final_response"] == "שמי אלון ברק."
    assert entry["status"] == "APPROVED"
    assert len(entry["attempts"]) == 1
    assert entry["attempts"][0]["attempt_number"] == 1
    assert entry["attempts"][0]["candidate_response"] == "שמי אלון ברק."

    # Verify file persistence
    with open(test_log_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["entry_id"] == entry["entry_id"]

    if test_log_path.exists():
        test_log_path.unlink()

    print("✓ test_inspection_logger passed")


def test_actor_mock_generation():
    """Verify Actor response flow with a mocked OpenAI client."""
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "סיימתי תואר שני במדעי המחשב בטכניון."
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    actor = Actor(client=mock_client, model="gpt-4o-mini")
    response = actor.generate_response(
        message="ספר לי על התואר השני שלך",
        history=[{"role": "user", "content": "שלום"}, {"role": "assistant", "content": "שלום!"}],
        session_id="mock_session",
    )

    assert response == "סיימתי תואר שני במדעי המחשב בטכניון."
    assert mock_client.chat.completions.create.called

    # Check call arguments
    call_args = mock_client.chat.completions.create.call_args[1]
    assert call_args["model"] == "gpt-4o-mini"
    messages = call_args["messages"]

    # 1 system + 2 history + 1 current message = 4 messages
    assert len(messages) == 4
    assert messages[0]["role"] == "system"
    assert actor.personal_summary in messages[0]["content"]
    assert actor.linkedin_profile in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert messages[2]["role"] == "assistant"
    assert messages[3]["role"] == "user"
    assert messages[3]["content"] == "ספר לי על התואר השני שלך"

    print("✓ test_actor_mock_generation passed")


if __name__ == "__main__":
    test_background_sources()
    test_system_prompt()
    test_history_normalization()
    test_inspection_logger()
    test_actor_mock_generation()
    print("\n All Part A unit & integration tests passed successfully!")
