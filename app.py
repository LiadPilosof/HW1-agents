"""
Hebrew Gradio Chat Interface for Part A (Actor - Response Generator).
Matches reference notebook style and launches a local web UI.
"""

import gradio as gr
from src.actor import chat_response
from src.config import DEFAULT_MODEL_NAME

EXAMPLES = [
    "ספר לי בקצרה על הרקע המקצועי שלך.",
    "איזו השכלה אקדמית יש לך, ומה היו נושאי התזה והקורסים הבולטים?",
    "באילו טכנולוגיות השתמשת בפרויקט DocuSense AI ומה היו תוצאותיו?",
    "מה הניסיון שלך בתחום RAG ו-LLM בעבודתך ב-TechNova Solutions?",
    "מה הציון שלך בבחינה הפסיכומטרית?",  # שאלת בדיקה למידע שאינו מופיע במקורות
]


def create_demo() -> gr.ChatInterface:
    """Creates the Hebrew Gradio ChatInterface."""
    demo = gr.ChatInterface(
        fn=chat_response,
        title="🤖 צ׳אט אישי - יוצר התשובה (Actor)",
        description=(
            f"מטלה 1: מערכות בינה מלאכותית (חלק א׳)<br>"
            f"שיחה עם הנציג הדיגיטלי של <b>אלון ברק</b> על בסיס פרופיל לינקדאין וסיכום אישי.<br>"
            f"<i>מודל שפה מוגדר: {DEFAULT_MODEL_NAME}</i>"
        ),
        chatbot=gr.Chatbot(rtl=True),
        textbox=gr.Textbox(
            placeholder="הקלד כאן את שאלתך (לדוגמה: ספר לי על ההשכלה שלך)...",
            submit_btn="שלח",
        ),
        examples=EXAMPLES,
    )
    return demo


if __name__ == "__main__":
    demo = create_demo()
    # Launch on local server
    demo.launch(server_name="127.0.0.1", inbrowser=False)
