"""
Standalone automated verification tests for Part B (Critic / Evaluator):
1. Valid, source-grounded candidate response (expects is_acceptable=True).
2. Candidate response with fabricated personal detail (expects is_acceptable=False with actionable feedback).
3. Candidate response correctly declaring missing info (expects is_acceptable=True).
4. Malformed/invalid payload verifying Pydantic ValidationError is caught as a technical error
   and never defaults to approval.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock
from pydantic import ValidationError

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluator import Evaluator, TechnicalEvaluationError
from src.logger import InspectionLogger
from src.schema import Evaluation


def test_valid_grounded_response():
    """Test 1: Valid source-grounded response must be approved (is_acceptable=True)."""
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.refusal = None
    mock_choice.message.parsed = Evaluation(
        is_acceptable=True,
        feedback="התשובה מבוססת במלואה על מקורות המידע (תואר שני בטכניון, ממוצע 94 ותזה על RAG) ועונה בדיוק על השאלה.",
    )
    mock_client.beta.chat.completions.parse.return_value = MagicMock(choices=[mock_choice])

    evaluator = Evaluator(client=mock_client)
    res = evaluator.evaluate(
        question="ספר לי על התואר השני שלך",
        candidate_response="סיימתי תואר שני במדעי המחשב בטכניון בהתמחות ב-AI עם ממוצע 94, ועבודת התזה שלי עסקה באופטימיזציה של מודלי שפה עבור RAG.",
    )

    assert isinstance(res, Evaluation)
    assert res.is_acceptable is True
    assert "במלואה על מקורות" in res.feedback or len(res.feedback) > 10
    print("✓ test_valid_grounded_response passed (is_acceptable=True)")


def test_fabricated_detail_response():
    """Test 2: Response with fabricated claims must be rejected with specific, actionable feedback."""
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.refusal = None
    mock_choice.message.parsed = Evaluation(
        is_acceptable=False,
        feedback="התשובה כוללת פרטים מומצאים: עבודה בגוגל במשך 5 שנים וניהול 20 עובדים אינם קיימים במקורות. יש לתקן ולציין שעבדת ב-DataPulse וב-InnoSoft בלבד.",
    )
    mock_client.beta.chat.completions.parse.return_value = MagicMock(choices=[mock_choice])

    evaluator = Evaluator(client=mock_client)
    res = evaluator.evaluate(
        question="איפה עבדת לפני TechNova?",
        candidate_response="לפני TechNova עבדתי כמהנדס AI בכיר בחברת Google במשך 5 שנים וניהלתי 20 עובדים.",
    )

    assert isinstance(res, Evaluation)
    assert res.is_acceptable is False
    # Ensure feedback is actionable and specific
    assert "Google" in res.feedback or "גוגל" in res.feedback or "מומצאים" in res.feedback
    assert len(res.feedback) > 20
    print("✓ test_fabricated_detail_response passed (is_acceptable=False with actionable feedback)")


def test_missing_info_response():
    """Test 3: Response stating information is missing from sources must be approved."""
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.refusal = None
    mock_choice.message.parsed = Evaluation(
        is_acceptable=True,
        feedback="התשובה מבהירה במפורש ובצדק שציון הפסיכומטרי אינו קיים במקורות המידע, ללא המצאת פרטים.",
    )
    mock_client.beta.chat.completions.parse.return_value = MagicMock(choices=[mock_choice])

    evaluator = Evaluator(client=mock_client)
    res = evaluator.evaluate(
        question="מה הציון שלך בבחינה הפסיכומטרית?",
        candidate_response="ציון הבחינה הפסיכומטרית שלי אינו מופיע במקורות המידע שסופקו, ולכן איני יכול לציין אותו.",
    )

    assert isinstance(res, Evaluation)
    assert res.is_acceptable is True
    print("✓ test_missing_info_response passed (is_acceptable=True for missing info handling)")


def test_technical_error_and_malformed_payload():
    """
    Test 4: Malformed output or schema failure must raise TechnicalEvaluationError
    and be recorded in the inspection log as TECHNICAL_ERROR (never treated as approval).
    """
    temp_log_path = Path("/tmp/test_eval_error_log.json")
    if temp_log_path.exists():
        temp_log_path.unlink()

    test_logger = InspectionLogger(log_path=temp_log_path)

    # Simulate an LLM output that is malformed (missing mandatory 'feedback' field)
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.refusal = None
    mock_choice.message.parsed = None
    # Intentionally missing the required 'feedback' field to trigger Pydantic ValidationError
    mock_choice.message.content = '{"is_acceptable": true}'
    mock_client.beta.chat.completions.parse.return_value = MagicMock(choices=[mock_choice])

    evaluator = Evaluator(client=mock_client)

    # Monkeypatch inspection logger to test log output
    from src import evaluator as eval_module
    orig_logger = eval_module.inspection_logger
    eval_module.inspection_logger = test_logger

    try:
        error_caught = False
        try:
            evaluator.evaluate(
                question="בדיקת תקלה טכנית",
                candidate_response="תשובה כלשהי",
            )
        except TechnicalEvaluationError as e:
            error_caught = True
            assert "ValidationError" in str(e) or "הערכת התשובה לא הושלמה" in str(e)

        assert error_caught, "Failed to raise TechnicalEvaluationError on malformed schema!"

        # Verify inspection log records technical error
        logs = test_logger.read_logs()
        assert len(logs) == 1
        entry = logs[0]
        assert entry["status"] == "TECHNICAL_ERROR"
        assert entry["attempts"][0]["is_acceptable"] is None  # NOT False and definitely NOT True
        assert "שגיאה טכנית" in entry["attempts"][0]["feedback"]

        print("✓ test_technical_error_and_malformed_payload passed (ValidationError halted execution safely)")

    finally:
        eval_module.inspection_logger = orig_logger
        if temp_log_path.exists():
            temp_log_path.unlink()


if __name__ == "__main__":
    test_valid_grounded_response()
    test_fabricated_detail_response()
    test_missing_info_response()
    test_technical_error_and_malformed_payload()
    print("\n All Part B Evaluator standalone tests passed successfully!")
