"""
Dedicated Test Script for Part B: Step 2 — Evaluator Instructions (SYSTEM_EVALUATOR & USER_EVALUATOR).

Verifies:
1. SYSTEM_EVALUATOR contains all 4 mandatory decision criteria:
   - a. Source Grounding (ביסוס במקורות)
   - b. Answering the Question (מענה לשאלה)
   - c. Handling Missing Information (טיפול במידע חסר)
   - d. Clarity & Style (בהירות וסגנון)
   - Actionable, concrete feedback requirement on rejection
   - Explicit rule to approve proper missing-info admissions
2. build_user_evaluator_prompt passes all 4 required context elements:
   - User's current question
   - Candidate response from Actor
   - Full background sources (personal_summary.txt and linkedin_profile.txt)
   - Ongoing conversation history (handling both empty and multi-turn history)
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import get_linkedin_profile, get_personal_summary
from src.prompts import SYSTEM_EVALUATOR, build_user_evaluator_prompt


def test_system_evaluator_criteria():
    """Verify SYSTEM_EVALUATOR explicitly enforces all 4 criteria and feedback rules."""
    prompt = SYSTEM_EVALUATOR

    # 1. Source Grounding (ביסוס במקורות)
    assert "ביסוס במקורות" in prompt, "Missing Criterion 1: ביסוס במקורות"
    assert "Source Grounding" in prompt or "מקורות" in prompt
    assert "Hallucinations" in prompt or "הומצאו" in prompt, "Missing explicit anti-hallucination instruction"

    # 2. Answering the Question (מענה לשאלה)
    assert "מענה לשאלה" in prompt, "Missing Criterion 2: מענה לשאלה"
    assert "Answering the Question" in prompt or "שאלת המשתמש" in prompt

    # 3. Handling Missing Information (טיפול במידע חסר)
    assert "טיפול במידע חסר" in prompt, "Missing Criterion 3: טיפול במידע חסר"
    assert "is_acceptable=True" in prompt, "Missing rule that valid missing-info statements should be approved"
    assert "חסר" in prompt

    # 4. Clarity & Style (בהירות וסגנון)
    assert "בהירות" in prompt, "Missing Criterion 4: בהירות"
    assert "סגנון" in prompt

    # Feedback Guidelines: Actionable, not generic
    assert "is_acceptable=False" in prompt
    assert "הנחיה מעשית" in prompt or "קונקרטית" in prompt, "Missing actionable feedback instruction"
    assert "התשובה אינה טובה" in prompt, "Missing explicit rule forbidding vague feedback"

    print("✓ test_system_evaluator_criteria passed (all 4 criteria and feedback rules verified)")


def test_user_evaluator_prompt_structure():
    """Verify build_user_evaluator_prompt embeds all required context."""
    summary = get_personal_summary()
    linkedin = get_linkedin_profile()

    question = "באיזה פרויקטים עבדת?"
    candidate = "עבדתי על DocuSense AI ו-SmartCode Reviewer."
    history = [
        {"role": "user", "content": "שלום"},
        {"role": "assistant", "content": "נעים להכיר, אני אלון ברק."},
    ]

    # Test with history
    user_prompt = build_user_evaluator_prompt(
        question=question,
        candidate_response=candidate,
        personal_summary=summary,
        linkedin_profile=linkedin,
        history=history,
    )

    # 1. Question
    assert question in user_prompt, "User question not found in user prompt"
    # 2. Candidate response
    assert candidate in user_prompt, "Candidate response not found in user prompt"
    # 3. Both background sources
    assert summary in user_prompt, "Personal summary background not found in user prompt"
    assert linkedin in user_prompt, "LinkedIn profile background not found in user prompt"
    # 4. History
    assert "שלום" in user_prompt, "History user turn not found in user prompt"
    assert "נעים להכיר, אני אלון ברק." in user_prompt, "History assistant turn not found in user prompt"

    # Test with empty history
    user_prompt_empty = build_user_evaluator_prompt(
        question=question,
        candidate_response=candidate,
        personal_summary=summary,
        linkedin_profile=linkedin,
        history=None,
    )
    assert "אין היסטוריה קודמת" in user_prompt_empty, "Missing empty-history indicator"
    assert question in user_prompt_empty
    assert candidate in user_prompt_empty

    print("✓ test_user_evaluator_prompt_structure passed (all 4 context sources verified)")


if __name__ == "__main__":
    test_system_evaluator_criteria()
    test_user_evaluator_prompt_structure()
    print("\n All Step 2 tests passed successfully!")
