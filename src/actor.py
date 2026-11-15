"""
Actor Module (Response Generator).
Handles LLM calls to generate answers grounded strictly in background sources,
mirroring the conventions of reference notebooks.
"""

from typing import Any, Dict, List, Optional
from openai import OpenAI

from src.config import (
    DEFAULT_MODEL_NAME,
    get_linkedin_profile,
    get_openai_client,
    get_personal_summary,
)
from src.logger import inspection_logger
from src.prompts import build_system_prompt


def normalize_history(history: Optional[List[Any]]) -> List[Dict[str, str]]:
    """
    Normalizes history from Gradio into standard OpenAI message dicts:
    [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    Supports both Gradio 'messages' format (list of dicts) and legacy pairs format (list of [u, a]).
    """
    if not history:
        return []

    normalized: List[Dict[str, str]] = []
    for item in history:
        if isinstance(item, dict):
            role = item.get("role")
            content = item.get("content")
            if role in ("user", "assistant") and content is not None:
                normalized.append({"role": role, "content": str(content)})
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            user_msg, bot_msg = item
            if user_msg is not None:
                normalized.append({"role": "user", "content": str(user_msg)})
            if bot_msg is not None:
                normalized.append({"role": "assistant", "content": str(bot_msg)})

    return normalized


class Actor:
    """Actor class responsible for generating grounded responses."""

    def __init__(self, client: Optional[OpenAI] = None, model: Optional[str] = None):
        self._client = client
        self.model = model or DEFAULT_MODEL_NAME
        self.personal_summary = get_personal_summary()
        self.linkedin_profile = get_linkedin_profile()
        self.system_prompt = build_system_prompt(
            personal_summary=self.personal_summary,
            linkedin_profile=self.linkedin_profile,
        )

    @property
    def client(self) -> OpenAI:
        """Lazy initialization of the OpenAI client if not injected."""
        if self._client is None:
            self._client = get_openai_client()
        return self._client

    def generate_response(
        self,
        message: str,
        history: Optional[List[Any]] = None,
        session_id: str = "default_session",
    ) -> str:
        """
        Generate candidate response for the user's message using background sources and history.
        Exact convention from reference notebooks:
        messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": message}]
        """
        formatted_history = normalize_history(history)
        messages = (
            [{"role": "system", "content": self.system_prompt}]
            + formatted_history
            + [{"role": "user", "content": message}]
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
        )

        candidate_response = response.choices[0].message.content or ""

        # In Part A, log this turn to the inspection log
        turn_index = (len(formatted_history) // 2) + 1
        inspection_logger.log_turn(
            user_message=message,
            candidate_response=candidate_response,
            final_response=candidate_response,
            status="APPROVED",
            session_id=session_id,
            turn_index=turn_index,
        )

        return candidate_response


_actor_instance: Optional[Actor] = None


def get_actor() -> Actor:
    """Returns singleton instance of Actor."""
    global _actor_instance
    if _actor_instance is None:
        _actor_instance = Actor()
    return _actor_instance


def chat_response(message: str, history: List[Any]) -> str:
    """Direct callable interface for Gradio chat, matching reference notebook conventions."""
    try:
        actor = get_actor()
        return actor.generate_response(message, history)
    except ValueError as e:
        return f"שגיאת תצורה: {e}"
    except Exception as e:
        return f"שגיאה בהפקת התשובה מהמודל: {e}"
