"""Pydantic models: the Critic's structured output (Part B) and a chat-turn type."""

from typing import Literal, NamedTuple, TypedDict

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatTurn(TypedDict):
    """One message of the conversation context sent to the models."""

    role: Literal["user", "assistant"]
    content: str


class RejectedDraft(NamedTuple):
    """A candidate the Critic rejected, handed back to the Actor for revision (Part C)."""

    response: str
    feedback: str


class Evaluation(BaseModel):
    """
    Structured output of the Critic (Part B).

    strict=True: `is_acceptable` must be a real JSON boolean (no "true"/1 coercion),
    so the decision is never inferred from loosely-typed text.
    """

    model_config = ConfigDict(strict=True)

    is_acceptable: bool = Field(
        description="החלטה האם התשובה המועמדת עומדת בכל קריטריוני ההערכה (True) או נדחית (False)."
    )
    feedback: str = Field(
        description=(
            "נימוק תמציתי להחלטה. במקרה של דחייה (False), חובה לפרט את הבעיה הספציפית "
            "(טענה לא מבוססת, פרט שהומצא, חוסר מענה לשאלה או סגנון לקוי) ולספק הנחיה "
            "מעשית לתיקון. משוב כללי כגון 'התשובה אינה טובה' אינו קביל."
        )
    )

    @field_validator("feedback")
    @classmethod
    def feedback_not_blank(cls, value: str) -> str:
        """A blank rationale is not a usable evaluation."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("feedback must not be empty")
        return stripped
