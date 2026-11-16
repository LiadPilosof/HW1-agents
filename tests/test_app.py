"""Gradio UI handlers: building the app, delivered history, and the verdict strip."""

import gradio as gr
import pytest

import app
from src.actor import Actor
from src.evaluator import Evaluator
from tests.fakes import completion, evaluation_json


@pytest.fixture
def wired(fake_client, log, monkeypatch):
    """Point the app's cached components at the fake client and temp log."""
    monkeypatch.setattr(app, "get_actor", lambda: Actor(client=fake_client))
    monkeypatch.setattr(app, "get_evaluator", lambda: Evaluator(client=fake_client))
    monkeypatch.setattr(app, "get_logger", lambda: log)

    def respond(actor_text, critic_json):
        fake_client.chat.completions.create.return_value = completion(actor_text)
        fake_client.chat.completions.parse.return_value = completion(critic_json)

    return respond


def test_create_demo_builds():
    assert isinstance(app.create_demo(), gr.Blocks)


def test_chat_trash_icon_also_resets_the_conversation():
    """Clearing via the chat's own icon must also drop the model context (session state)."""
    config: dict = dict(app.create_demo().get_config_file())
    (chatbot_id,) = [c["id"] for c in config["components"] if c.get("type") == "chatbot"]
    clear_deps = [d for d in config["dependencies"] if (chatbot_id, "clear") in d["targets"]]
    assert len(clear_deps) == 1
    session_ids = {c["id"] for c in config["components"] if c.get("type") == "state"}
    assert session_ids & set(clear_deps[0]["outputs"])


def test_stage_question_shows_message_and_locks_composer():
    textbox, button, display, pending, verdict = app.stage_question("  שאלה  ", [])
    assert display == [{"role": "user", "content": "שאלה"}]
    assert pending == "שאלה"
    assert textbox["interactive"] is False and textbox["value"] == ""
    assert button["interactive"] is False
    assert verdict == app.VERDICT_PENDING


@pytest.mark.parametrize("text", ["", "   ", None])
def test_blank_input_is_ignored(text):
    *_, pending, _ = app.stage_question(text, [])
    assert pending is None
    assert app.answer(None, [], None) == (gr.skip(), gr.skip(), gr.skip())


def test_approved_answer_is_displayed_and_kept_as_context(wired):
    wired("עבדתי ב-DataPulse.", evaluation_json(True, "מבוסס"))
    display, session, verdict = app.answer(
        "איפה עבדת?", [{"role": "user", "content": "איפה עבדת?"}], None
    )
    assert display[-1] == {"role": "assistant", "content": "עבדתי ב-DataPulse."}
    assert session["context"] == [
        {"role": "user", "content": "איפה עבדת?"},
        {"role": "assistant", "content": "עבדתי ב-DataPulse."},
    ]
    assert session["questions"] == 1
    assert "approved" in verdict and "מבוסס" in verdict


def test_follow_up_receives_previous_approved_answer(wired, fake_client):
    wired("עבדתי ב-DataPulse.", evaluation_json(True, "מבוסס"))
    _, session, _ = app.answer("איפה עבדת?", [], None)
    wired("שם הייתי ML Engineer.", evaluation_json(True, "מבוסס"))
    _, session, _ = app.answer("ומה עשית שם?", [], session)
    messages = fake_client.chat.completions.create.call_args.kwargs["messages"]
    assert [m["content"] for m in messages[1:]] == [
        "איפה עבדת?",
        "עבדתי ב-DataPulse.",
        "ומה עשית שם?",
    ]
    assert session["questions"] == 2


def test_rejected_answer_is_not_shown_or_added_to_context(wired):
    wired("עבדתי ב-Google.", evaluation_json(False, "Google אינה במקורות"))
    display, session, verdict = app.answer("איפה עבדת?", [], None)
    assert "Google" not in display[-1]["content"]
    assert session["context"] == []
    assert "rejected" in verdict


def test_technical_error_is_shown_clearly(wired):
    wired("טיוטה", '{"is_acceptable": true}')
    display, session, verdict = app.answer("שאלה", [], None)
    assert "שגיאה טכנית" in display[-1]["content"]
    assert session["context"] == []
    assert "error" in verdict


def test_error_details_are_labelled_and_left_to_right():
    html = app.render_verdict("error", "t", "x", "ValidationError: feedback missing")
    assert "פרטי השגיאה" in html and 'dir="ltr"' in html
    assert "הצגת המשוב" in app.render_verdict("rejected", "t", "x", "feedback")


def test_verdict_escapes_model_text():
    html = app.render_verdict("rejected", "t", "x", "<script>alert(1)</script>")
    assert "<script>" not in html and "&lt;script&gt;" in html


def test_reset_clears_conversation():
    display, session, pending, verdict, textbox = app.reset()
    assert display == [] and session is None and pending is None
    assert verdict == app.VERDICT_IDLE and textbox["interactive"] is True
