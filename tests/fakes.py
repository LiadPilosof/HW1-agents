"""Builders for fake OpenAI chat-completion responses."""

import json
from types import SimpleNamespace


def completion(content: str | None, refusal: str | None = None) -> SimpleNamespace:
    """Shape of a chat completion: .choices[0].message.{content,refusal,parsed}."""
    message = SimpleNamespace(content=content, refusal=refusal, parsed=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def evaluation_json(is_acceptable: object, feedback: object = "נימוק") -> str:
    return json.dumps({"is_acceptable": is_acceptable, "feedback": feedback}, ensure_ascii=False)
