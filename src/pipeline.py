"""
Handling of one user question: Actor draft -> Critic decision -> what the user sees.

Scope is Parts A and B only: one draft and one evaluation per question.
- Approved (is_acceptable=True after schema validation): the answer is shown.
- Rejected: the draft is NOT shown; the user gets a notice. (The revision loop
  that would retry with the feedback belongs to Part C and is not implemented.)
- Technical error (Actor call fails, or the Critic output is missing/invalid):
  handling stops with a clear message; nothing is recorded as an approval.
Every outcome is written to the separate inspection log.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from src.actor import Actor
from src.evaluator import Evaluator, TechnicalEvaluationError
from src.logger import InspectionLogger
from src.schema import ChatTurn, Evaluation

Status = Literal["APPROVED", "REJECTED", "TECHNICAL_ERROR"]

REJECTED_NOTICE = (
    "התשובה שהופקה לא עברה את בדיקת המעריך ולכן אינה מוצגת. הטיוטה והמשוב נשמרו ביומן הבדיקה."
)
ACTOR_ERROR_NOTICE = "לא ניתן היה להפיק תשובה עקב שגיאה טכנית בקריאה למודל. השאלה לא נענתה."
CRITIC_ERROR_NOTICE = (
    "ההערכה לא הושלמה עקב שגיאה טכנית, ולכן התשובה לא אושרה ואינה מוצגת. השאלה לא נענתה."
)


@dataclass(frozen=True)
class TurnResult:
    status: Status
    message: str  # what the chat shows: the approved answer, or a notice
    candidate_response: str | None = None
    evaluation: Evaluation | None = None
    error: str | None = None

    @property
    def approved(self) -> bool:
        return self.status == "APPROVED"


def handle_question(
    question: str,
    history: Sequence[ChatTurn],
    *,
    actor: Actor,
    evaluator: Evaluator,
    logger: InspectionLogger,
    session_id: str,
    turn_index: int,
) -> TurnResult:
    """Run one Actor draft and one Critic evaluation, log it, and return the outcome."""
    base_record = {
        "session_id": session_id,
        "turn_index": turn_index,
        "question": question,
        "actor_model": actor.model,
        "critic_model": evaluator.model,
    }

    try:
        candidate = actor.generate(question, history)
    except Exception as error:
        message = f"{type(error).__name__}: {error}"
        logger.append(
            {
                **base_record,
                "status": "TECHNICAL_ERROR",
                "candidate_response": None,
                "evaluation_completed": False,
                "evaluation": None,
                "technical_error": {"stage": "actor", "message": message},
                "displayed_response": None,
            }
        )
        return TurnResult("TECHNICAL_ERROR", ACTOR_ERROR_NOTICE, error=message)

    try:
        evaluation = evaluator.evaluate(question, candidate, history)
    except TechnicalEvaluationError as error:
        logger.append(
            {
                **base_record,
                "status": "TECHNICAL_ERROR",
                "candidate_response": candidate,
                "evaluation_completed": False,
                "evaluation": None,
                "technical_error": {"stage": "critic", "message": str(error)},
                "displayed_response": None,
            }
        )
        return TurnResult(
            "TECHNICAL_ERROR", CRITIC_ERROR_NOTICE, candidate_response=candidate, error=str(error)
        )

    status: Status = "APPROVED" if evaluation.is_acceptable else "REJECTED"
    shown = candidate if evaluation.is_acceptable else None
    logger.append(
        {
            **base_record,
            "status": status,
            "candidate_response": candidate,
            "evaluation_completed": True,
            "evaluation": evaluation.model_dump(),
            "technical_error": None,
            "displayed_response": shown,
        }
    )
    return TurnResult(
        status,
        shown if shown is not None else REJECTED_NOTICE,
        candidate_response=candidate,
        evaluation=evaluation,
    )
