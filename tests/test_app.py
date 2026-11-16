"""Gradio UI handlers: building the app, the loop's progress, delivered history, verdicts."""

import gradio as gr
import pytest

import app
from src.actor import Actor
from src.evaluator import Evaluator
from src.pipeline import EXHAUSTED_NOTICE, Attempt
from src.schema import Evaluation
from tests.fakes import completion, evaluation_json

APPROVE = evaluation_json(True, "מבוסס")


@pytest.fixture
def wired(fake_client, log, monkeypatch):
    """Point the app's cached components at the fake client and temp log."""
    monkeypatch.setattr(app, "get_actor", lambda: Actor(client=fake_client))
    monkeypatch.setattr(app, "get_evaluator", lambda: Evaluator(client=fake_client))
    monkeypatch.setattr(app, "get_logger", lambda: log)

    def respond(actor_texts: list[str], critic_jsons: list[str]):
        fake_client.chat.completions.create.side_effect = [completion(t) for t in actor_texts]
        fake_client.chat.completions.parse.side_effect = [completion(c) for c in critic_jsons]

    return respond


def answer_updates(question, display, session) -> list[tuple]:
    """All UI updates the answer generator yields, in order."""
    return list(app.answer(question, display, session))


def final(question, display, session) -> tuple:
    return answer_updates(question, display, session)[-1]


# --- Building and wiring -------------------------------------------------------------


def test_create_demo_builds():
    assert isinstance(app.create_demo(), gr.Blocks)


def test_chat_trash_icon_also_resets_the_conversation():
    """Clearing via the chat's own icon must also drop the model context (session state)."""
    config: dict = dict(app.create_demo().get_config_file())
    (chatbot_id,) = [c["id"] for c in config["components"] if c.get("type") == "chatbot"]
    clear_deps = [
        d
        for d in config["dependencies"]
        if (chatbot_id, "clear") in d["targets"] and str(d["api_name"]).startswith("reset")
    ]
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
    assert answer_updates(None, [], None) == [(gr.skip(), gr.skip(), gr.skip())]


# --- Loop outcomes in the UI ---------------------------------------------------------


def test_approved_first_time_is_displayed_and_kept_as_context(wired):
    wired(["עבדתי ב-DataPulse."], [APPROVE])
    updates = answer_updates("איפה עבדת?", [{"role": "user", "content": "איפה עבדת?"}], None)
    assert len(updates) == 1, "no revision progress when the first draft is approved"
    display, session, verdict = updates[0]
    assert display[-1] == {"role": "assistant", "content": "עבדתי ב-DataPulse."}
    assert session["context"] == [
        {"role": "user", "content": "איפה עבדת?"},
        {"role": "assistant", "content": "עבדתי ב-DataPulse."},
    ]
    assert "approved" in verdict and "בניסיון 1 מתוך 3" in verdict


def test_revision_shows_progress_then_the_approved_revision(wired):
    wired(
        ["עבדתי ב-Google.", "עבדתי ב-DataPulse."],
        [evaluation_json(False, "Google אינה במקורות"), APPROVE],
    )
    progress, last = answer_updates("איפה עבדת?", [], None)

    chat_update, _, revising = progress
    assert chat_update == gr.skip(), "the chat is not touched while revising"
    assert "pending" in revising and "ניסיון 2 מתוך 3" in revising
    assert "Google אינה במקורות" in revising  # feedback so far is visible
    assert "עבדתי ב-Google." not in revising  # drafts stay in the log only

    display, session, verdict = last
    assert display[-1]["content"] == "עבדתי ב-DataPulse."
    assert "Google" not in str(display)
    assert session["context"][-1]["content"] == "עבדתי ב-DataPulse."
    assert "בניסיון 2 מתוך 3" in verdict
    assert "ניסיון 1: נדחה" in verdict and "ניסיון 2: אושר" in verdict


def test_exhausted_attempts_show_a_notice_and_keep_context_clean(wired):
    rejection = evaluation_json(False, "פרט מומצא")
    wired(["א", "ב", "ג"], [rejection, rejection, rejection])
    updates = answer_updates("איפה עבדת?", [], None)
    assert len(updates) == 3  # two "revising" updates + the final state
    display, session, verdict = updates[-1]
    assert display[-1]["content"] == EXHAUSTED_NOTICE
    assert session["context"] == []
    assert "exhausted" in verdict and verdict.count("נדחה") == 3


def test_new_question_after_exhaustion_starts_fresh(wired, fake_client):
    rejection = evaluation_json(False, "פרט מומצא")
    wired(["א", "ב", "ג", "עבדתי ב-DataPulse."], [rejection, rejection, rejection, APPROVE])
    _, session, _ = final("שאלה 1", [], None)
    _, session, verdict = final("איפה עבדת?", [], session)
    assert "בניסיון 1 מתוך 3" in verdict
    assert session["questions"] == 2
    assert session["context"] == [
        {"role": "user", "content": "איפה עבדת?"},
        {"role": "assistant", "content": "עבדתי ב-DataPulse."},
    ]
    # The unanswered first question is not part of the model's context.
    last_actor_messages = fake_client.chat.completions.create.call_args.kwargs["messages"]
    assert "שאלה 1" not in str(last_actor_messages)


def test_follow_up_receives_previous_approved_answer(wired, fake_client):
    wired(["עבדתי ב-DataPulse.", "שם הייתי ML Engineer."], [APPROVE, APPROVE])
    _, session, _ = final("איפה עבדת?", [], None)
    _, session, _ = final("ומה עשית שם?", [], session)
    messages = fake_client.chat.completions.create.call_args.kwargs["messages"]
    assert [m["content"] for m in messages[1:]] == [
        "איפה עבדת?",
        "עבדתי ב-DataPulse.",
        "ומה עשית שם?",
    ]


def test_technical_error_is_shown_clearly(wired):
    wired(["טיוטה"], ['{"is_acceptable": true}'])
    updates = answer_updates("שאלה", [], None)
    assert len(updates) == 1
    display, session, verdict = updates[0]
    assert "שגיאה טכנית" in display[-1]["content"]
    assert session["context"] == []
    assert "error" in verdict and "ההערכה לא הושלמה" in verdict


# --- Verdict rendering ---------------------------------------------------------------


def test_error_details_are_labelled_and_left_to_right():
    attempts = (Attempt(1, "x", error_stage="critic", error="ValidationError: feedback missing"),)
    html = app.render_verdict("error", "t", "x", attempts)
    assert "פרטי השגיאה" in html and 'dir="ltr"' in html


def test_verdict_escapes_model_text():
    evil = Evaluation(is_acceptable=False, feedback="<script>alert(1)</script>")
    html = app.render_verdict("exhausted", "t", "x", (Attempt(1, "draft", evil),))
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "משוב המעריך" in html


def test_reset_clears_conversation():
    display, session, pending, verdict, textbox, send = app.reset()
    assert display == [] and session is None and pending is None
    assert verdict == app.VERDICT_IDLE
    assert textbox["interactive"] is True and send["interactive"] is True


def test_reset_cancels_an_answer_in_progress():
    """Both reset controls must cancel the running answer, or it would restore the old chat."""
    config: dict = dict(app.create_demo().get_config_file())
    deps: list[dict] = config["dependencies"]
    answer_ids = {d["id"] for d in deps if str(d.get("api_name")).startswith("answer")}
    reset_targets = [d["targets"][0] for d in deps if str(d.get("api_name")).startswith("reset")]
    assert len(answer_ids) == 3 and len(reset_targets) == 2
    for target in reset_targets:
        cancelled = {i for d in deps if d["targets"] == [target] for i in d["cancels"]}
        assert answer_ids <= cancelled


def test_launch_allows_the_assets_folder(monkeypatch):
    """Avatars must load during streamed updates even when started from another directory."""
    captured: dict = {}
    monkeypatch.setattr(gr.Blocks, "launch", lambda _self, **kwargs: captured.update(kwargs))
    app.launch_app(server_port=1234)
    assert str(app.ASSETS_DIR) in captured["allowed_paths"]
    assert captured["server_port"] == 1234 and captured["theme"] is app.THEME
