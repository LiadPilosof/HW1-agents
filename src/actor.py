"""Actor (response generator): drafts a grounded answer from sources + history + question.

For a revision (Part C) the Actor also receives its rejected draft and the Critic's
feedback, and is asked for a corrected version of the same answer.
"""

from collections.abc import Sequence

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from src.config import (
    ACTOR_MODEL_NAME,
    get_linkedin_profile,
    get_openai_client,
    get_personal_summary,
)
from src.prompts import build_revision_request, build_system_prompt
from src.schema import ChatTurn, RejectedDraft


class Actor:
    """Generates candidate responses grounded in the background sources."""

    def __init__(self, client: OpenAI | None = None, model: str | None = None):
        self._client = client
        self.model = model or ACTOR_MODEL_NAME
        self.personal_summary = get_personal_summary()
        self.linkedin_profile = get_linkedin_profile()
        self.system_prompt = build_system_prompt(self.personal_summary, self.linkedin_profile)

    @property
    def client(self) -> OpenAI:
        """Create the OpenAI client on first use unless one was injected."""
        if self._client is None:
            self._client = get_openai_client()
        return self._client

    def build_messages(
        self,
        question: str,
        history: Sequence[ChatTurn] = (),
        rejected: RejectedDraft | None = None,
    ) -> list[ChatCompletionMessageParam]:
        """
        System prompt (with sources) + conversation history + the current question.

        With `rejected`, the rejected draft follows as the Actor's own previous turn,
        then the Critic's feedback with a request for a corrected version.
        """
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": self.system_prompt}
        ]
        for turn in history:
            if turn["role"] == "user":
                messages.append({"role": "user", "content": turn["content"]})
            else:
                messages.append({"role": "assistant", "content": turn["content"]})
        messages.append({"role": "user", "content": question})
        if rejected is not None:
            messages.append({"role": "assistant", "content": rejected.response})
            messages.append({"role": "user", "content": build_revision_request(rejected.feedback)})
        return messages

    def generate(
        self,
        question: str,
        history: Sequence[ChatTurn] = (),
        rejected: RejectedDraft | None = None,
    ) -> str:
        """Return the candidate response. Raises on API failure or an empty answer."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.build_messages(question, history, rejected),
        )
        content = (response.choices[0].message.content or "").strip()
        if not content:
            raise ValueError("The Actor model returned an empty response.")
        return content
