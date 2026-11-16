"""
Generate -> evaluate -> revise loop for one user question (Part C).

Up to MAX_ATTEMPTS generations per question, the first answer included. Every new
candidate is evaluated again; the decision comes only from the validated
`Evaluation.is_acceptable`.

- Approved: the candidate is shown and handling ends.
- Rejected with attempts left: the rejected draft and its feedback go back to the
  Actor (with the question, sources and history) for a corrected version.
- Rejected on the last attempt: handling ends with ATTEMPTS_EXHAUSTED; no rejected
  draft is ever shown as an answer.
- Technical error (Actor call fails, or the Critic output is missing/invalid):
  handling ends immediately with TECHNICAL_ERROR; nothing counts as an approval.

Each question is written to the inspection log once, with every attempt.
"""

from collections.abc import Generator, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from src.actor import Actor
from src.evaluator import Evaluator, TechnicalEvaluationError
from src.logger import InspectionLogger
from src.schema import ChatTurn, Evaluation, RejectedDraft

MAX_ATTEMPTS = 3

Status = Literal["APPROVED", "ATTEMPTS_EXHAUSTED", "TECHNICAL_ERROR"]

EXHAUSTED_NOTICE = (
    f"לא התקבלה תשובה מאושרת במסגרת מגבלת {MAX_ATTEMPTS} הניסיונות, ולכן לא מוצגת תשובה. "
    "הטיוטות והמשוב נשמרו ביומן הבדיקה."
)
ACTOR_ERROR_NOTICE = "לא ניתן היה להפיק תשובה עקב שגיאה טכנית בקריאה למודל. השאלה לא נענתה."
CRITIC_ERROR_NOTICE = (
    "ההערכה לא הושלמה עקב שגיאה טכנית, ולכן התשובה לא אושרה ואינה מוצגת. השאלה לא נענתה."
)


@dataclass(frozen=True)
class Attempt:
    """One generation and its evaluation (or the technical error that stopped it)."""

    number: int
    candidate: str | None = None
    evaluation: Evaluation | None = None
    error_stage: Literal["setup", "actor", "critic"] | None = None
    error: str | None = None

    @property
    def evaluation_completed(self) -> bool:
        return self.evaluation is not None

    @property
    def approved(self) -> bool:
        return self.evaluation is not None and self.evaluation.is_acceptable

    def to_log(self) -> dict[str, Any]:
        return {
            "attempt_number": self.number,
            "candidate_response": self.candidate,
            "evaluation_completed": self.evaluation_completed,
            # No content decision is recorded when the evaluation did not complete.
            "is_acceptable": self.evaluation.is_acceptable if self.evaluation else None,
            "feedback": self.evaluation.feedback if self.evaluation else None,
            "technical_error": (
                {"stage": self.error_stage, "message": self.error} if self.error else None
            ),
        }


@dataclass(frozen=True)
class TurnResult:
    status: Status
    message: str  # what the chat shows: the approved answer, or a notice
    attempts: tuple[Attempt, ...] = ()

    @property
    def approved(self) -> bool:
        return self.status == "APPROVED"


def iter_question(
    question: str,
    history: Sequence[ChatTurn],
    *,
    actor: Actor,
    evaluator: Evaluator,
    logger: InspectionLogger,
    session_id: str,
    turn_index: int,
    scenario_id: str = "interactive",
    max_attempts: int = MAX_ATTEMPTS,
) -> Generator[Attempt, None, TurnResult]:
    """
    Run the loop for one question, yielding each Attempt as it completes.

    The generator's return value (StopIteration.value) is the final TurnResult.
    """
    attempts: list[Attempt] = []

    def finish(status: Status, message: str) -> TurnResult:
        result = TurnResult(status, message, tuple(attempts))
        logger.append(
            {
                "scenario_id": scenario_id,
                "session_id": session_id,
                "turn_index": turn_index,
                "question": question,
                "status": status,
                "attempts_used": len(attempts),
                "max_attempts": max_attempts,
                "actor_model": actor.model,
                "critic_model": evaluator.model,
                "attempts": [a.to_log() for a in attempts],
                "displayed_response": message if result.approved else None,
            }
        )
        return result

    rejected: RejectedDraft | None = None
    for number in range(1, max_attempts + 1):
        try:
            candidate = actor.generate(question, history, rejected)
        except Exception as error:
            attempt = Attempt(number, error_stage="actor", error=f"{type(error).__name__}: {error}")
            attempts.append(attempt)
            yield attempt
            return finish("TECHNICAL_ERROR", ACTOR_ERROR_NOTICE)

        try:
            evaluation = evaluator.evaluate(question, candidate, history)
        except TechnicalEvaluationError as error:
            attempt = Attempt(number, candidate, error_stage="critic", error=str(error))
            attempts.append(attempt)
            yield attempt
            return finish("TECHNICAL_ERROR", CRITIC_ERROR_NOTICE)

        attempt = Attempt(number, candidate, evaluation)
        attempts.append(attempt)
        yield attempt
        if evaluation.is_acceptable:
            return finish("APPROVED", candidate)
        rejected = RejectedDraft(candidate, evaluation.feedback)

    return finish("ATTEMPTS_EXHAUSTED", EXHAUSTED_NOTICE)


def handle_question(
    question: str,
    history: Sequence[ChatTurn],
    *,
    actor: Actor,
    evaluator: Evaluator,
    logger: InspectionLogger,
    session_id: str,
    turn_index: int,
    scenario_id: str = "interactive",
    max_attempts: int = MAX_ATTEMPTS,
) -> TurnResult:
    """Run the whole loop for one question and return the final result."""
    run = iter_question(
        question,
        history,
        actor=actor,
        evaluator=evaluator,
        logger=logger,
        session_id=session_id,
        turn_index=turn_index,
        scenario_id=scenario_id,
        max_attempts=max_attempts,
    )
    while True:
        try:
            next(run)
        except StopIteration as done:
            return done.value
