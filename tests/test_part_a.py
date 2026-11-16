"""Part A: background sources, Actor prompt, conversation context, inspection log."""

import json
import threading

import pytest

from src import config
from src.actor import Actor
from src.config import get_linkedin_profile, get_personal_summary
from src.logger import InspectionLogger
from src.prompts import SCOPE_RULES, STYLE_RULES, build_system_prompt
from src.schema import ChatTurn
from tests.fakes import completion

# --- A.1 Background sources ---------------------------------------------------------


def test_background_files_exist_and_are_marked_as_sample():
    linkedin, summary = get_linkedin_profile(), get_personal_summary()
    for text in (linkedin, summary):
        assert "פרופיל לדוגמה" in text


def test_linkedin_profile_covers_education_experience_skills_projects():
    linkedin = get_linkedin_profile()
    for section in ("השכלה", "ניסיון תעסוקתי", "מיומנויות", "פרויקטים"):
        assert section in linkedin


def test_personal_summary_is_about_half_a_page():
    words = len(get_personal_summary().split())
    assert 150 <= words <= 450, f"personal summary has {words} words"


def test_missing_source_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        config.load_file_content(tmp_path / "missing.txt")


# --- A.2 Actor system prompt --------------------------------------------------------


def test_system_prompt_defines_role_style_grounding_and_missing_info():
    summary, linkedin = get_personal_summary(), get_linkedin_profile()
    prompt = build_system_prompt(summary, linkedin)
    assert summary in prompt and linkedin in prompt
    assert "# תפקיד" in prompt
    assert STYLE_RULES in prompt
    assert "ביסוס קפדני במקורות" in prompt
    assert "אין להמציא" in prompt
    assert "טיפול במידע חסר" in prompt
    assert "אינו מופיע במקורות" in prompt


def test_system_prompt_limits_scope_to_the_profile_owner():
    prompt = build_system_prompt(get_personal_summary(), get_linkedin_profile())
    assert SCOPE_RULES in prompt
    assert "מזג אוויר" in SCOPE_RULES  # off-topic example
    assert "אל תציע לבדוק, לחפש" in SCOPE_RULES  # no offers to look things up


# --- A.3 Conversation context -------------------------------------------------------


def test_actor_sends_sources_history_and_question(fake_client):
    fake_client.chat.completions.create.return_value = completion("סיימתי תואר שני בטכניון.")
    actor = Actor(client=fake_client, model="test-actor")
    history: list[ChatTurn] = [
        {"role": "user", "content": "איפה למדת?"},
        {"role": "assistant", "content": "בטכניון ובאוניברסיטת תל אביב."},
    ]

    answer = actor.generate("ובאיזה ממוצע סיימת שם?", history)

    assert answer == "סיימתי תואר שני בטכניון."
    kwargs = fake_client.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "test-actor"
    messages = kwargs["messages"]
    assert [m["role"] for m in messages] == ["system", "user", "assistant", "user"]
    assert actor.personal_summary in messages[0]["content"]
    assert actor.linkedin_profile in messages[0]["content"]
    assert messages[1]["content"] == "איפה למדת?"
    assert messages[2]["content"] == "בטכניון ובאוניברסיטת תל אביב."
    assert messages[3]["content"] == "ובאיזה ממוצע סיימת שם?"


def test_actor_first_question_has_no_history(fake_client):
    fake_client.chat.completions.create.return_value = completion("שלום")
    Actor(client=fake_client).generate("מי אתה?")
    roles = [m["role"] for m in fake_client.chat.completions.create.call_args.kwargs["messages"]]
    assert roles == ["system", "user"]


@pytest.mark.parametrize("content", [None, "", "   "])
def test_actor_empty_response_is_an_error(fake_client, content):
    fake_client.chat.completions.create.return_value = completion(content)
    with pytest.raises(ValueError):
        Actor(client=fake_client).generate("שאלה")


def test_missing_api_key_gives_clear_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "your_openai_api_key_here")
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        config.get_openai_client()
    monkeypatch.delenv("OPENAI_API_KEY")
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        config.get_openai_client()


# --- A.4 Separate inspection log ----------------------------------------------------


def test_log_creates_parent_dir_and_appends(log):
    first = log.append({"question": "א"})
    log.append({"question": "ב"})
    data = json.loads(log.log_path.read_text(encoding="utf-8"))
    assert [e["question"] for e in data] == ["א", "ב"]
    assert data[0]["entry_id"] == first["entry_id"]
    assert "timestamp" in first


def test_log_stores_hebrew_readably(log):
    log.append({"question": "שלום"})
    assert "שלום" in log.log_path.read_text(encoding="utf-8")


def test_log_reads_missing_or_corrupt_file_as_empty(tmp_path):
    logger = InspectionLogger(tmp_path / "log.json")
    assert logger.read_logs() == []
    logger.log_path.write_text("{not json", encoding="utf-8")
    assert logger.read_logs() == []


def test_log_is_safe_under_concurrent_writes(log):
    threads = [threading.Thread(target=log.append, args=({"n": i},)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(e["n"] for e in log.read_logs()) == list(range(20))
