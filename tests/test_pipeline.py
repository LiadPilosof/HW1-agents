"""Part C: the generate -> evaluate -> revise loop (offline, scripted model replies)."""

import json

import pytest

from src.actor import Actor
from src.evaluator import Evaluator
from src.pipeline import (
    ACTOR_ERROR_NOTICE,
    CRITIC_ERROR_NOTICE,
    EXHAUSTED_NOTICE,
    MAX_ATTEMPTS,
    handle_question,
    iter_question,
)
from src.prompts import build_revision_request
from src.schema import ChatTurn, RejectedDraft
from tests.fakes import completion, evaluation_json

QUESTION = "ומה התפקיד שלך שם?"
HISTORY: list[ChatTurn] = [
    {"role": "user", "content": "איפה אתה עובד?"},
    {"role": "assistant", "content": "ב-TechNova Solutions."},
]
APPROVE = evaluation_json(True, "מבוסס על הפרופיל")


def reject(n: int) -> str:
    return evaluation_json(
        False, f"משוב {n}: התפקיד שהומצא אינו במקורות; יש לציין Senior AI Engineer."
    )


def script(fake_client, actor_replies, critic_replies):
    """Queue model replies; an Exception instance in a list is raised at that call."""

    def wrap(item):
        return item if isinstance(item, Exception) else completion(item)

    fake_client.chat.completions.create.side_effect = [wrap(x) for x in actor_replies]
    fake_client.chat.completions.parse.side_effect = [wrap(x) for x in critic_replies]


def components(fake_client, log, **overrides):
    return {
        "actor": Actor(client=fake_client, model="actor-m"),
        "evaluator": Evaluator(client=fake_client, model="critic-m"),
        "logger": log,
        "session_id": "s1",
        "turn_index": 2,
        "scenario_id": "unit",
        **overrides,
    }


def run(fake_client, log, actor_replies, critic_replies, **overrides):
    script(fake_client, actor_replies, critic_replies)
    result = handle_question(QUESTION, HISTORY, **components(fake_client, log, **overrides))
    entries = log.read_logs()
    assert len(entries) == 1, "exactly one log entry per question"
    return result, entries[0]


def actor_calls(fake_client):
    return [c.kwargs["messages"] for c in fake_client.chat.completions.create.call_args_list]


def critic_calls(fake_client):
    return [c.kwargs["messages"] for c in fake_client.chat.completions.parse.call_args_list]


# --- End state: approved -------------------------------------------------------------


def test_approved_on_first_attempt(fake_client, log):
    result, entry = run(fake_client, log, ["טיוטה 1"], [APPROVE])
    assert result.approved and result.message == "טיוטה 1"
    assert len(actor_calls(fake_client)) == 1 and len(critic_calls(fake_client)) == 1
    assert entry["status"] == "APPROVED"
    assert entry["displayed_response"] == "טיוטה 1"
    assert entry["attempts_used"] == 1 and entry["max_attempts"] == MAX_ATTEMPTS
    assert entry["attempts"] == [
        {
            "attempt_number": 1,
            "candidate_response": "טיוטה 1",
            "evaluation_completed": True,
            "is_acceptable": True,
            "feedback": "מבוסס על הפרופיל",
            "technical_error": None,
        }
    ]
    assert (entry["scenario_id"], entry["session_id"], entry["turn_index"]) == ("unit", "s1", 2)
    assert entry["question"] == QUESTION
    assert (entry["actor_model"], entry["critic_model"]) == ("actor-m", "critic-m")


def test_rejected_draft_and_feedback_reach_the_actor_and_revision_is_reevaluated(fake_client, log):
    result, entry = run(
        fake_client, log, ["אני ה-CTO.", "אני Senior AI Engineer."], [reject(1), APPROVE]
    )

    assert result.approved and result.message == "אני Senior AI Engineer."
    first, second = actor_calls(fake_client)
    # The revision keeps the system prompt (sources), history and question...
    assert second[: len(first)] == first
    # ...and adds the rejected draft and the Critic's feedback.
    assert second[len(first)] == {"role": "assistant", "content": "אני ה-CTO."}
    assert second[len(first) + 1] == {
        "role": "user",
        "content": build_revision_request(json.loads(reject(1))["feedback"]),
    }
    # The new candidate is evaluated again.
    assert "אני Senior AI Engineer." in critic_calls(fake_client)[1][1]["content"]

    assert [a["is_acceptable"] for a in entry["attempts"]] == [False, True]
    assert entry["attempts"][0]["candidate_response"] == "אני ה-CTO."
    assert entry["attempts"][0]["feedback"].startswith("משוב 1")
    assert entry["displayed_response"] == "אני Senior AI Engineer."


# --- End state: attempts exhausted ---------------------------------------------------


def test_three_rejections_end_the_loop_without_showing_a_draft(fake_client, log):
    drafts = ["טיוטה 1", "טיוטה 2", "טיוטה 3"]
    result, entry = run(fake_client, log, drafts, [reject(1), reject(2), reject(3)])

    assert result.status == "ATTEMPTS_EXHAUSTED" and not result.approved
    assert result.message == EXHAUSTED_NOTICE
    assert not any(d in result.message for d in drafts)
    assert len(actor_calls(fake_client)) == MAX_ATTEMPTS == 3
    assert len(critic_calls(fake_client)) == 3
    assert entry["status"] == "ATTEMPTS_EXHAUSTED"
    assert entry["displayed_response"] is None
    assert [a["candidate_response"] for a in entry["attempts"]] == drafts
    assert [a["is_acceptable"] for a in entry["attempts"]] == [False, False, False]
    assert [a["attempt_number"] for a in entry["attempts"]] == [1, 2, 3]


def test_each_revision_uses_the_latest_rejection(fake_client, log):
    run(fake_client, log, ["טיוטה 1", "טיוטה 2", "טיוטה 3"], [reject(1), reject(2), reject(3)])
    third = actor_calls(fake_client)[2]
    assert third[-2] == {"role": "assistant", "content": "טיוטה 2"}
    assert "משוב 2" in third[-1]["content"]
    assert "טיוטה 1" not in str(third)


def test_max_attempts_is_respected(fake_client, log):
    result, entry = run(fake_client, log, ["טיוטה"], [reject(1)], max_attempts=1)
    assert result.status == "ATTEMPTS_EXHAUSTED"
    assert entry["attempts_used"] == 1 and entry["max_attempts"] == 1


# --- End state: technical error ------------------------------------------------------


@pytest.mark.parametrize("bad_output", ['{"is_acceptable": false}', "{broken", None])
def test_invalid_critic_output_on_a_revision_stops_the_loop(fake_client, log, bad_output):
    result, entry = run(
        fake_client, log, ["טיוטה 1", "טיוטה 2", "טיוטה 3"], [reject(1), bad_output]
    )

    assert result.status == "TECHNICAL_ERROR" and result.message == CRITIC_ERROR_NOTICE
    assert len(actor_calls(fake_client)) == 2, "no further attempts after a technical error"
    assert entry["status"] == "TECHNICAL_ERROR" and entry["displayed_response"] is None
    failed = entry["attempts"][1]
    assert failed["evaluation_completed"] is False
    assert failed["is_acceptable"] is None and failed["feedback"] is None
    assert failed["technical_error"]["stage"] == "critic"
    assert failed["candidate_response"] == "טיוטה 2"


def test_actor_failure_on_a_revision_stops_the_loop(fake_client, log):
    result, entry = run(fake_client, log, ["טיוטה 1", TimeoutError("timed out")], [reject(1)])
    assert result.status == "TECHNICAL_ERROR" and result.message == ACTOR_ERROR_NOTICE
    assert len(critic_calls(fake_client)) == 1
    failed = entry["attempts"][1]
    assert failed["candidate_response"] is None
    assert failed["technical_error"] == {"stage": "actor", "message": "TimeoutError: timed out"}


def test_actor_failure_on_first_attempt_skips_evaluation(fake_client, log):
    result, entry = run(fake_client, log, [ConnectionError("down")], [])
    assert result.status == "TECHNICAL_ERROR"
    assert not fake_client.chat.completions.parse.called
    assert entry["attempts_used"] == 1


# --- Integration with Parts A-B ------------------------------------------------------


def test_history_and_sources_reach_every_attempt(fake_client, log):
    run(fake_client, log, ["טיוטה 1", "טיוטה 2"], [reject(1), APPROVE])
    for messages in actor_calls(fake_client):
        assert messages[0]["role"] == "system" and "פרופיל לדוגמה" in messages[0]["content"]
        assert messages[1]["content"] == "איפה אתה עובד?"
        assert messages[3]["content"] == QUESTION
    for _system, user in critic_calls(fake_client):
        assert "ב-TechNova Solutions." in user["content"]  # history
        assert "פרופיל לדוגמה" in user["content"]  # sources
    # The Critic judges each candidate on its own: attempt 2 sees only the revision.
    assert "טיוטה 1" not in critic_calls(fake_client)[1][1]["content"]


def test_new_question_resets_the_attempt_counter(fake_client, log):
    kwargs = components(fake_client, log)
    script(fake_client, ["א", "ב", "ג", "ד"], [reject(1), reject(2), reject(3), APPROVE])
    first = handle_question("שאלה 1", HISTORY, **kwargs)
    second = handle_question("שאלה 2", HISTORY, **{**kwargs, "turn_index": 3})
    assert first.status == "ATTEMPTS_EXHAUSTED" and second.approved
    entries = log.read_logs()
    assert [e["attempts_used"] for e in entries] == [3, 1]
    assert entries[1]["attempts"][0]["attempt_number"] == 1
    # The new question starts without any revision context.
    assert actor_calls(fake_client)[3][-1] == {"role": "user", "content": "שאלה 2"}


def test_iter_question_yields_each_attempt_then_returns_the_result(fake_client, log):
    script(fake_client, ["טיוטה 1", "טיוטה 2"], [reject(1), APPROVE])
    run_ = iter_question(QUESTION, HISTORY, **components(fake_client, log))
    first = next(run_)
    assert first.number == 1 and not first.approved and log.read_logs() == []
    second = next(run_)
    assert second.number == 2 and second.approved
    with pytest.raises(StopIteration) as done:
        next(run_)
    assert done.value.value.attempts == (first, second)
    assert len(log.read_logs()) == 1


# --- Actor revision messages ---------------------------------------------------------


def test_actor_revision_messages(fake_client):
    actor = Actor(client=fake_client)
    plain = actor.build_messages(QUESTION, HISTORY)
    revised = actor.build_messages(
        QUESTION, HISTORY, RejectedDraft("אני ה-CTO.", "CTO אינו במקורות")
    )
    assert revised[: len(plain)] == plain
    assert revised[-2] == {"role": "assistant", "content": "אני ה-CTO."}
    assert revised[-1] == {"role": "user", "content": build_revision_request("CTO אינו במקורות")}


def test_revision_request_asks_for_a_clean_corrected_answer():
    request = build_revision_request("הומצא ציון")
    assert "הומצא ציון" in request
    assert "גרסה מתוקנת" in request
    assert "בלי להזכיר את המעריך" in request  # the user must not see review chatter
