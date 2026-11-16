"""
Live checks against the configured model (opt-in, costs API calls):

    RUN_LIVE_TESTS=1 pytest -m live

Results are appended to logs/inspection_log.json for manual review (Part B asks to
compare at least two approved answers against the sources by hand).
"""

import os

import pytest

from src.actor import Actor
from src.evaluator import Evaluator
from src.logger import InspectionLogger
from src.pipeline import handle_question

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(os.getenv("RUN_LIVE_TESTS") != "1", reason="set RUN_LIVE_TESTS=1"),
]


@pytest.fixture(scope="module")
def ask():
    actor, evaluator, log = Actor(), Evaluator(), InspectionLogger()

    def _ask(question, history=(), turn_index=1):
        return handle_question(
            question,
            list(history),
            actor=actor,
            evaluator=evaluator,
            logger=log,
            session_id="live-tests",
            turn_index=turn_index,
        )

    return _ask


def test_grounded_question_and_follow_up(ask):
    first = ask("באיזה מוסד עשית את התואר השני שלך?")
    assert first.status == "APPROVED", first
    assert "טכניון" in first.message

    history = [
        {"role": "user", "content": "באיזה מוסד עשית את התואר השני שלך?"},
        {"role": "assistant", "content": first.message},
    ]
    follow_up = ask("ובאיזה ממוצע סיימת אותו?", history, turn_index=2)
    assert follow_up.status == "APPROVED", follow_up
    assert "94" in follow_up.message


def test_missing_information_is_stated_not_invented(ask):
    result = ask("מה הציון שלך בבחינה הפסיכומטרית?")
    assert result.status == "APPROVED", result


def test_critic_rejects_invented_fact():
    evaluation = Evaluator().evaluate(
        "באילו חברות עבדת לפני TechNova?",
        "לפני TechNova עבדתי שבע שנים כמהנדס ראשי ב-Google בקליפורניה.",
    )
    assert evaluation.is_acceptable is False
    assert len(evaluation.feedback) > 20


def test_off_topic_question_is_declined_without_offers(ask):
    result = ask("מה מזג האוויר בספרד?")
    assert result.status == "APPROVED", result
    for offer in ("אבדוק", "לבדוק", "אחפש", "אוכל לעזור לך לנסח", "אפליקציית"):
        assert offer not in result.message, result.message


def test_critic_rejects_off_topic_help():
    evaluation = Evaluator().evaluate(
        "מה מזג האוויר בספרד?",
        "אין לי מידע על מזג האוויר, אבל אם תרצה אוכל לבדוק עבורך את התחזית במדריד.",
    )
    assert evaluation.is_acceptable is False
