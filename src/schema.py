"""
Pydantic Schema Module for Structured Evaluator (Critic) Output.
Adheres strictly to Assignment 1 Part B requirements.
"""

from pydantic import BaseModel, Field


class Evaluation(BaseModel):
    """
    Structured output schema for the Critic / Evaluator.
    Mandated by Assignment 1: Part B.
    """

    is_acceptable: bool = Field(
        description="החלטה האם התשובה המועמדת עומדת בכל קריטריוני ההערכה (True) או נדחית (False)."
    )
    feedback: str = Field(
        description=(
            "נימוק תמציתי להחלטה. במקרה של דחייה (False), חובה לפרט את הבעיה הספציפית "
            "(טענה לא מבוססת, פרט שהומצא, חוסר מענה לשאלה או סגנון לקוי) ולספק הנחיה מעשית לתיקון. "
            "משוב כללי כגון 'התשובה אינה טובה' אינו קביל."
        )
    )
