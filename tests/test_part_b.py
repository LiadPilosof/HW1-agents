"""Part B: Critic prompts, the Evaluation schema, and strict technical-error handling."""

import pytest
from pydantic import ValidationError

from src.config import get_linkedin_profile, get_personal_summary
from src.evaluator import Evaluator, TechnicalEvaluationError
from src.prompts import SCOPE_RULES, STYLE_RULES, SYSTEM_EVALUATOR, build_user_evaluator_prompt
from src.schema import ChatTurn, Evaluation
from tests.fakes import completion, evaluation_json

# --- Evaluator System: criteria א–ד and feedback rules -------------------------------


@pytest.mark.parametrize(
    "criterion", ["ביסוס במקורות", "מענה לשאלה", "טיפול במידע חסר", "בהירות וסגנון"]
)
def test_system_evaluator_has_each_criterion(criterion):
    assert criterion in SYSTEM_EVALUATOR


def test_system_evaluator_rules():
    assert "שהומצאו" in SYSTEM_EVALUATOR  # invented facts -> reject
    assert "יש לאשר אותה (is_acceptable=True)" in SYSTEM_EVALUATOR  # honest "missing" -> approve
    assert "הנחיה מעשית" in SYSTEM_EVALUATOR  # actionable feedback
    assert "התשובה אינה טובה" in SYSTEM_EVALUATOR  # vague feedback forbidden
    assert STYLE_RULES in SYSTEM_EVALUATOR  # same style rules the Actor got
    assert SCOPE_RULES in SYSTEM_EVALUATOR  # same topic scope the Actor got
    assert "מציעה לבדוק, לחפש או לבצע פעולה" in SYSTEM_EVALUATOR  # such offers -> reject


# --- Evaluator User: question, candidate, history, sources ---------------------------


def test_user_evaluator_prompt_contains_all_material():
    summary, linkedin = get_personal_summary(), get_linkedin_profile()
    history: list[ChatTurn] = [
        {"role": "user", "content": "שאלה קודמת"},
        {"role": "assistant", "content": "תשובה קודמת"},
    ]
    prompt = build_user_evaluator_prompt("שאלה נוכחית", "תשובה מועמדת", summary, linkedin, history)
    for part in ("שאלה נוכחית", "תשובה מועמדת", summary, linkedin):
        assert part in prompt
    assert "משתמש: שאלה קודמת" in prompt
    assert "יוצר התשובה (Actor): תשובה קודמת" in prompt


def test_user_evaluator_prompt_without_history():
    prompt = build_user_evaluator_prompt("ש", "ת", "s", "l")
    assert "אין היסטוריה קודמת" in prompt


# --- Evaluation schema ---------------------------------------------------------------


def test_schema_has_exactly_the_two_required_fields():
    schema = Evaluation.model_json_schema()
    assert set(schema["properties"]) == {"is_acceptable", "feedback"}
    assert set(schema["required"]) == {"is_acceptable", "feedback"}
    assert schema["properties"]["is_acceptable"]["type"] == "boolean"
    assert schema["properties"]["feedback"]["type"] == "string"


@pytest.mark.parametrize(
    "payload",
    [
        '{"is_acceptable": true}',  # missing feedback
        '{"feedback": "x"}',  # missing decision
        evaluation_json("true"),  # string, not boolean
        evaluation_json(1),  # number, not boolean
        evaluation_json(True, "   "),  # blank feedback
        "not json at all",
    ],
)
def test_schema_rejects_invalid_payloads(payload):
    with pytest.raises(ValidationError):
        Evaluation.model_validate_json(payload)


# --- Evaluator behaviour -------------------------------------------------------------


def make_evaluator(fake_client, content, refusal=None) -> Evaluator:
    fake_client.chat.completions.parse.return_value = completion(content, refusal)
    return Evaluator(client=fake_client, model="test-critic")


def test_evaluator_uses_structured_output_with_both_messages(fake_client):
    evaluator = make_evaluator(fake_client, evaluation_json(True, "מבוסס"))
    history: list[ChatTurn] = [
        {"role": "user", "content": "קודם"},
        {"role": "assistant", "content": "תשובה"},
    ]
    evaluator.evaluate("שאלה", "מועמדת", history)

    kwargs = fake_client.chat.completions.parse.call_args.kwargs
    assert kwargs["model"] == "test-critic"
    assert kwargs["response_format"] is Evaluation
    system, user = kwargs["messages"]
    assert system == {"role": "system", "content": SYSTEM_EVALUATOR}
    assert "מועמדת" in user["content"] and "משתמש: קודם" in user["content"]
    assert evaluator.linkedin_profile in user["content"]


@pytest.mark.parametrize("decision", [True, False])
def test_evaluator_returns_validated_decision(fake_client, decision):
    result = make_evaluator(fake_client, evaluation_json(decision, "נימוק מפורט")).evaluate(
        "ש", "ת"
    )
    assert result == Evaluation(is_acceptable=decision, feedback="נימוק מפורט")


def test_decision_comes_from_boolean_not_feedback_text(fake_client):
    content = evaluation_json(False, "התשובה מאושרת ונכונה, אך הומצא שם החברה Google.")
    assert make_evaluator(fake_client, content).evaluate("ש", "ת").is_acceptable is False


@pytest.mark.parametrize(
    "content,refusal",
    [
        ('{"is_acceptable": true}', None),  # missing required field
        (evaluation_json("yes"), None),  # wrong type
        ("{broken", None),  # unparseable
        (None, None),  # empty
        (None, "I can't help with that."),  # refusal
    ],
)
def test_invalid_output_is_a_technical_error_never_an_approval(fake_client, content, refusal):
    with pytest.raises(TechnicalEvaluationError):
        make_evaluator(fake_client, content, refusal).evaluate("ש", "ת")


def test_api_failure_is_a_technical_error(fake_client):
    fake_client.chat.completions.parse.side_effect = ConnectionError("network down")
    with pytest.raises(TechnicalEvaluationError, match="network down"):
        Evaluator(client=fake_client).evaluate("ש", "ת")
