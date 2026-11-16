"""
Response Evaluator Module (Critic).
Evaluates candidate responses from the Actor against background sources, conversation history,
and quality criteria, returning a structured Pydantic Evaluation object.
Adheres strictly to Assignment 1 Part B requirements.
"""

from typing import Any, Dict, List, Optional
from openai import OpenAI, OpenAIError
from pydantic import ValidationError

from src.config import (
    CRITIC_MODEL_NAME,
    get_linkedin_profile,
    get_openai_client,
    get_personal_summary,
)
from src.logger import inspection_logger
from src.prompts import SYSTEM_EVALUATOR, build_user_evaluator_prompt
from src.schema import Evaluation


class TechnicalEvaluationError(Exception):
    """Raised when an evaluation cannot be completed due to API failure, parsing error, or schema invalidity."""
    pass


def normalize_history_for_evaluator(history: Optional[List[Any]]) -> List[Dict[str, str]]:
    """Normalizes chat history to a clean list of role/content dicts for evaluator prompt."""
    if not history:
        return []

    from src.actor import extract_text

    normalized: List[Dict[str, str]] = []
    for item in history:
        if isinstance(item, dict):
            role = item.get("role")
            content = item.get("content")
            if role in ("user", "assistant") and content is not None:
                normalized.append({"role": role, "content": extract_text(content)})
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            user_msg, bot_msg = item
            if user_msg is not None:
                normalized.append({"role": "user", "content": extract_text(user_msg)})
            if bot_msg is not None:
                normalized.append({"role": "assistant", "content": extract_text(bot_msg)})

    return normalized


class Evaluator:
    """Critic / Evaluator class responsible for assessing candidate responses."""

    def __init__(self, client: Optional[OpenAI] = None, model: Optional[str] = None):
        self._client = client
        self.model = model or CRITIC_MODEL_NAME
        self.personal_summary = get_personal_summary()
        self.linkedin_profile = get_linkedin_profile()
        self.system_prompt = SYSTEM_EVALUATOR

    @property
    def client(self) -> OpenAI:
        """Lazy initialization of the OpenAI client if not injected."""
        if self._client is None:
            self._client = get_openai_client()
        return self._client

    def evaluate(
        self,
        question: str,
        candidate_response: str,
        history: Optional[List[Any]] = None,
        session_id: Optional[str] = None,
        turn_index: int = 1,
        attempt_number: int = 1,
        scenario_id: Optional[str] = None,
    ) -> Evaluation:
        """
        Evaluates a candidate response against the background sources and criteria.
        Returns a validated Evaluation Pydantic model.
        In case of API failure or schema invalidity, records a technical error and raises TechnicalEvaluationError.
        """
        formatted_history = normalize_history_for_evaluator(history)
        user_prompt = build_user_evaluator_prompt(
            question=question,
            candidate_response=candidate_response,
            personal_summary=self.personal_summary,
            linkedin_profile=self.linkedin_profile,
            history=formatted_history,
        )

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            # Call OpenAI Structured Outputs API
            response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=messages,
                response_format=Evaluation,
            )

            choice = response.choices[0]
            if getattr(choice.message, "refusal", None):
                raise TechnicalEvaluationError(f"Model refused evaluation: {choice.message.refusal}")

            evaluation = choice.message.parsed

            # Fallback parsing if message.parsed is None but content exists
            if evaluation is None:
                content = choice.message.content
                if not content:
                    raise TechnicalEvaluationError("Empty response returned by evaluator model.")
                evaluation = Evaluation.model_validate_json(content)

            # Explicit validation check on required types
            if not isinstance(evaluation, Evaluation):
                raise TechnicalEvaluationError("Evaluator output is not a valid Evaluation instance.")

            # Record successful evaluation in inspection log
            inspection_logger.log_evaluation(
                user_message=question,
                candidate_response=candidate_response,
                evaluation=evaluation,
                session_id=session_id,
                turn_index=turn_index,
                attempt_number=attempt_number,
                scenario_id=scenario_id,
            )

            return evaluation

        except (ValidationError, OpenAIError, ValueError, Exception) as error:
            error_msg = f"{type(error).__name__}: {str(error)}"
            # Record technical error in inspection log (explicitly noting evaluation did not complete)
            inspection_logger.log_evaluation(
                user_message=question,
                candidate_response=candidate_response,
                technical_error=error_msg,
                session_id=session_id,
                turn_index=turn_index,
                attempt_number=attempt_number,
                scenario_id=scenario_id,
            )
            # Re-raise to ensure downstream processes halt and never treat technical failure as approval
            raise TechnicalEvaluationError(
                f"הערכת התשובה לא הושלמה עקב שגיאה טכנית: {error_msg}"
            ) from error


_evaluator_instance: Optional[Evaluator] = None


def get_evaluator() -> Evaluator:
    """Returns singleton instance of Evaluator."""
    global _evaluator_instance
    if _evaluator_instance is None:
        _evaluator_instance = Evaluator()
    return _evaluator_instance


def evaluate_response(
    question: str,
    candidate_response: str,
    history: Optional[List[Any]] = None,
    session_id: Optional[str] = None,
    turn_index: int = 1,
    attempt_number: int = 1,
    scenario_id: Optional[str] = None,
) -> Evaluation:
    """
    Direct evaluation function for Critic component.
    Returns validated Evaluation or raises TechnicalEvaluationError.
    """
    evaluator = get_evaluator()
    return evaluator.evaluate(
        question=question,
        candidate_response=candidate_response,
        history=history,
        session_id=session_id,
        turn_index=turn_index,
        attempt_number=attempt_number,
        scenario_id=scenario_id,
    )
