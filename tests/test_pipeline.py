"""One question end-to-end (offline): Actor draft -> Critic decision -> shown text + log."""

import pytest

from src.actor import Actor
from src.evaluator import Evaluator
from src.pipeline import (
    ACTOR_ERROR_NOTICE,
    CRITIC_ERROR_NOTICE,
    REJECTED_NOTICE,
    handle_question,
)
from tests.fakes import completion, evaluation_json

HISTORY = [
    {"role": "user", "content": "איפה אתה עובד?"},
    {"role": "assistant", "content": "ב-TechNova Solutions."},
]


def run(fake_client, log, critic_content="", actor_content="טיוטה", history=HISTORY):
    fake_client.chat.completions.create.return_value = completion(actor_content)
    fake_client.chat.completions.parse.return_value = completion(critic_content)
    result = handle_question(
        "ומה התפקיד שלך שם?",
        history,
        actor=Actor(client=fake_client, model="actor-m"),
        evaluator=Evaluator(client=fake_client, model="critic-m"),
        logger=log,
        session_id="s1",
        turn_index=2,
    )
    entries = log.read_logs()
    assert len(entries) == 1, "exactly one log entry per question"
    return result, entries[0]


def test_approved_answer_is_shown_and_logged(fake_client, log):
    result, entry = run(fake_client, log, evaluation_json(True, "מבוסס על הפרופיל"))
    assert result.approved and result.message == "טיוטה"
    assert entry["status"] == "APPROVED"
    assert entry["evaluation"] == {"is_acceptable": True, "feedback": "מבוסס על הפרופיל"}
    assert entry["evaluation_completed"] is True
    assert entry["displayed_response"] == "טיוטה"
    assert entry["candidate_response"] == "טיוטה"
    assert (entry["session_id"], entry["turn_index"]) == ("s1", 2)
    assert (entry["actor_model"], entry["critic_model"]) == ("actor-m", "critic-m")


def test_rejected_draft_is_not_shown_but_logged_with_feedback(fake_client, log):
    feedback = "הומצא תפקיד CTO שאינו במקורות; יש לציין Senior AI Engineer."
    result, entry = run(fake_client, log, evaluation_json(False, feedback), "אני ה-CTO.")
    assert result.status == "REJECTED"
    assert result.message == REJECTED_NOTICE
    assert "CTO" not in result.message
    assert entry["status"] == "REJECTED"
    assert entry["candidate_response"] == "אני ה-CTO."
    assert entry["evaluation"]["feedback"] == feedback
    assert entry["displayed_response"] is None


@pytest.mark.parametrize("bad_output", ['{"is_acceptable": true}', "{broken", None])
def test_critic_failure_stops_handling_without_approval(fake_client, log, bad_output):
    result, entry = run(fake_client, log, bad_output)
    assert result.status == "TECHNICAL_ERROR" and not result.approved
    assert result.message == CRITIC_ERROR_NOTICE
    assert entry["status"] == "TECHNICAL_ERROR"
    assert entry["evaluation_completed"] is False
    assert entry["evaluation"] is None  # no content decision is recorded
    assert entry["technical_error"]["stage"] == "critic"
    assert entry["candidate_response"] == "טיוטה"
    assert entry["displayed_response"] is None


def test_actor_failure_stops_before_evaluation(fake_client, log):
    fake_client.chat.completions.create.side_effect = TimeoutError("timed out")
    result = handle_question(
        "שאלה",
        [],
        actor=Actor(client=fake_client),
        evaluator=Evaluator(client=fake_client),
        logger=log,
        session_id="s",
        turn_index=1,
    )
    assert result.status == "TECHNICAL_ERROR" and result.message == ACTOR_ERROR_NOTICE
    assert not fake_client.chat.completions.parse.called
    (entry,) = log.read_logs()
    assert entry["technical_error"]["stage"] == "actor"
    assert "timed out" in entry["technical_error"]["message"]


def test_history_reaches_both_actor_and_critic(fake_client, log):
    run(fake_client, log, evaluation_json(True, "ok"))
    actor_messages = fake_client.chat.completions.create.call_args.kwargs["messages"]
    assert actor_messages[1]["content"] == "איפה אתה עובד?"
    critic_user = fake_client.chat.completions.parse.call_args.kwargs["messages"][1]["content"]
    assert "ב-TechNova Solutions." in critic_user
