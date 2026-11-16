"""
Critic (response evaluator), Part B.

Returns a schema-validated `Evaluation`. Any failure to obtain one (API error, refusal,
unparseable JSON, missing/invalid field) raises TechnicalEvaluationError, so a failed
validation can never be mistaken for an approval.
"""

from collections.abc import Sequence

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from src.config import (
    CRITIC_MODEL_NAME,
    get_linkedin_profile,
    get_openai_client,
    get_personal_summary,
)
from src.prompts import SYSTEM_EVALUATOR, build_user_evaluator_prompt
from src.schema import ChatTurn, Evaluation


class TechnicalEvaluationError(Exception):
    """The evaluation did not complete; no content decision exists."""


class Evaluator:
    """Assesses a candidate response against the sources, the question and the history."""

    def __init__(self, client: OpenAI | None = None, model: str | None = None):
        self._client = client
        self.model = model or CRITIC_MODEL_NAME
        self.personal_summary = get_personal_summary()
        self.linkedin_profile = get_linkedin_profile()

    @property
    def client(self) -> OpenAI:
        """Create the OpenAI client on first use unless one was injected."""
        if self._client is None:
            self._client = get_openai_client()
        return self._client

    def build_messages(
        self, question: str, candidate_response: str, history: Sequence[ChatTurn] = ()
    ) -> list[ChatCompletionMessageParam]:
        """Evaluator System + Evaluator User messages."""
        user_prompt = build_user_evaluator_prompt(
            question=question,
            candidate_response=candidate_response,
            personal_summary=self.personal_summary,
            linkedin_profile=self.linkedin_profile,
            history=history,
        )
        return [
            {"role": "system", "content": SYSTEM_EVALUATOR},
            {"role": "user", "content": user_prompt},
        ]

    def evaluate(
        self, question: str, candidate_response: str, history: Sequence[ChatTurn] = ()
    ) -> Evaluation:
        """Return a validated Evaluation, or raise TechnicalEvaluationError."""
        try:
            response = self.client.chat.completions.parse(
                model=self.model,
                messages=self.build_messages(question, candidate_response, history),
                response_format=Evaluation,
            )
            message = response.choices[0].message
            if message.refusal:
                raise ValueError(f"Model refused to evaluate: {message.refusal}")

            # Re-validate the raw JSON ourselves so the decision always comes from the
            # schema check, independent of how the SDK populated `parsed`.
            if not message.content:
                raise ValueError("Evaluator returned an empty response.")
            return Evaluation.model_validate_json(message.content)
        except Exception as error:
            raise TechnicalEvaluationError(f"{type(error).__name__}: {error}") from error
