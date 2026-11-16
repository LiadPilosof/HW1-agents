"""
Hebrew Gradio chat for Assignment 1, Parts A and B.

Every question gets one Actor draft and one Critic evaluation (see src/pipeline.py).
The chat shows user messages and the answers delivered to them; drafts, decisions and
feedback go to the separate inspection log, with the latest verdict shown in the
alert under the chat. Visual design tokens live in src/theme.py.
"""

import html
import uuid
from functools import cache
from pathlib import Path
from typing import Any

import gradio as gr

from src.actor import Actor
from src.config import ACTOR_MODEL_NAME, CRITIC_MODEL_NAME
from src.evaluator import Evaluator
from src.logger import InspectionLogger
from src.pipeline import TurnResult, handle_question
from src.theme import CSS, THEME

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
AVATARS = (str(ASSETS_DIR / "user_avatar.svg"), str(ASSETS_DIR / "bot_avatar.svg"))

EXAMPLE_QUESTIONS = [
    "ספר לי על ההשכלה האקדמית שלך ועל נושא התזה.",
    "מה הניסיון שלך בפיתוח ארכיטקטורות RAG ב-TechNova?",
    "באילו טכנולוגיות השתמשת בפרויקט DocuSense AI?",
    "מה הציון שלך בבחינה הפסיכומטרית?",
]

ICONS = {
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "x": '<path d="M18 6 6 18M6 6l12 12"/>',
    "alert": '<path d="M12 9v4M12 17h.01"/>'
    '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 16v-4M12 8h.01"/>',
    "loader": '<path d="M21 12a9 9 0 1 1-6.2-8.6"/>',
    "shield": '<path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z"/><path d="m9 12 2 2 4-4"/>',
    "chevron": '<path d="m6 9 6 6 6-6"/>',
}


def icon(name: str) -> str:
    """Inline stroke icon; colour follows the surrounding text."""
    return f'<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">{ICONS[name]}</svg>'


HEADER_HTML = f"""
<header class="app-header">
  <div class="identity">
    <div class="monogram" aria-hidden="true">אב</div>
    <div>
      <h1>אלון ברק</h1>
      <p><bdi>Senior AI Engineer</bdi> ב-<bdi>TechNova Solutions</bdi></p>
    </div>
  </div>
  <div class="badges">
    <span class="badge badge-accent">{icon("shield")}תשובות נבדקות מול המקורות</span>
    <span class="badge">פרופיל לדוגמה</span>
  </div>
</header>
"""

EMPTY_STATE = (
    "**שאלו על השכלה, ניסיון, מיומנויות או פרויקטים**\n\n"
    "כל תשובה נבדקת מול הפרופיל והסיכום האישי לפני שהיא מוצגת."
)

FOOTER_HTML = (
    f'<p class="footer-note">יוצר התשובה: <bdi>{html.escape(ACTOR_MODEL_NAME)}</bdi>. '
    f"מעריך התשובות: <bdi>{html.escape(CRITIC_MODEL_NAME)}</bdi>. "
    "טיוטות, החלטות ומשוב נשמרים בקובץ <bdi>logs/inspection_log.json</bdi>.</p>"
)

VERDICT_ICONS = {
    "idle": "info",
    "pending": "loader",
    "approved": "check",
    "rejected": "x",
    "error": "alert",
}


def render_verdict(kind: str, title: str, text: str = "", details: str = "") -> str:
    """HTML for the verdict alert. kind: idle | pending | approved | rejected | error.

    `details` is the Critic's feedback, or the technical error message for kind="error".
    """
    body = [f'<p class="verdict-title">{html.escape(title)}</p>']
    if text:
        body.append(f'<p class="verdict-text">{html.escape(text)}</p>')
    if kind == "pending":
        body.append('<div class="skeleton"></div><div class="skeleton short"></div>')
    if details:
        is_error = kind == "error"
        label = "פרטי השגיאה" if is_error else "הצגת המשוב"
        attrs = ' class="feedback technical" dir="ltr"' if is_error else ' class="feedback"'
        body.append(
            f"<details><summary>{label}{icon('chevron')}</summary>"
            f"<p{attrs}>{html.escape(details)}</p></details>"
        )
    return (
        f'<div class="verdict {kind}" role="status" aria-live="polite">'
        f'<span class="verdict-icon">{icon(VERDICT_ICONS[kind])}</span>'
        f'<div class="verdict-body">{"".join(body)}</div></div>'
    )


VERDICT_IDLE = render_verdict("idle", "טרם נשאלה שאלה", "כאן תופיע החלטת המעריך על התשובה האחרונה.")
VERDICT_PENDING = render_verdict(
    "pending", "בודק את התשובה", "יוצר התשובה מנסח טיוטה והמעריך בודק אותה מול המקורות."
)


def verdict_for(result: TurnResult) -> str:
    """Map a pipeline outcome to the verdict alert."""
    feedback = result.evaluation.feedback if result.evaluation else ""
    if result.status == "APPROVED":
        return render_verdict(
            "approved", "התשובה אושרה", "המעריך מצא שהתשובה מבוססת על המקורות.", feedback
        )
    if result.status == "REJECTED":
        return render_verdict(
            "rejected", "התשובה נדחתה ולא הוצגה", "הטיוטה והמשוב נשמרו ביומן הבדיקה.", feedback
        )
    return render_verdict(
        "error", "שגיאה טכנית, ההערכה לא הושלמה", result.message, result.error or ""
    )


def new_session() -> dict[str, Any]:
    """Per-browser conversation state: log id, question counter, approved context."""
    return {"id": uuid.uuid4().hex[:12], "questions": 0, "context": []}


# Created once, on first use, so importing the app has no side effects.
@cache
def get_actor() -> Actor:
    return Actor()


@cache
def get_evaluator() -> Evaluator:
    return Evaluator()


@cache
def get_logger() -> InspectionLogger:
    return InspectionLogger()


def stage_question(text: str, display: list) -> tuple:
    """Step 1: show the user's message right away and lock the composer."""
    question = (text or "").strip()
    if not question:
        return gr.skip(), gr.skip(), gr.skip(), None, gr.skip()
    return (
        gr.update(value="", interactive=False),
        gr.update(interactive=False),
        [*(display or []), {"role": "user", "content": question}],
        question,
        VERDICT_PENDING,
    )


def stage_example(display: list, evt: gr.SelectData) -> tuple:
    """Step 1 for a clicked example question."""
    value = evt.value
    text = value.get("text", "") if isinstance(value, dict) else str(value)
    return stage_question(text, display)


def answer(question: str | None, display: list, session: dict | None) -> tuple:
    """Step 2: run Actor -> Critic once and show the outcome."""
    if not question:
        return gr.skip(), gr.skip(), gr.skip()
    session = session or new_session()
    session["questions"] += 1
    try:
        result = handle_question(
            question,
            session["context"],
            actor=get_actor(),
            evaluator=get_evaluator(),
            logger=get_logger(),
            session_id=session["id"],
            turn_index=session["questions"],
        )
    except Exception as error:  # e.g. a background source file is missing
        result = TurnResult(
            "TECHNICAL_ERROR",
            "לא ניתן היה לטפל בשאלה עקב שגיאה בהגדרות המערכת.",
            error=f"{type(error).__name__}: {error}",
        )
    if result.approved:
        # Only delivered answers become context for follow-up questions.
        session["context"] = [
            *session["context"],
            {"role": "user", "content": question},
            {"role": "assistant", "content": result.message},
        ]
    display = [*(display or []), {"role": "assistant", "content": result.message}]
    return display, session, verdict_for(result)


def unlock() -> tuple:
    """Step 3: re-enable the composer."""
    return gr.update(interactive=True), gr.update(interactive=True)


def reset() -> tuple:
    return [], None, None, VERDICT_IDLE, gr.update(value="", interactive=True)


def create_demo() -> gr.Blocks:
    with gr.Blocks(title="אלון ברק | צ׳אט אישי") as demo:
        session = gr.State(None)
        pending = gr.State(None)

        gr.HTML(HEADER_HTML, padding=False)
        with gr.Column(elem_classes=["chat-panel"]):
            chatbot = gr.Chatbot(
                rtl=True,
                height="min(60vh, 560px)",
                show_label=False,
                placeholder=EMPTY_STATE,
                examples=[{"text": q} for q in EXAMPLE_QUESTIONS],
                avatar_images=AVATARS,
                buttons=["copy"],
                elem_classes=["chat-window"],
            )
            with gr.Row(elem_classes=["composer"], equal_height=True):
                msg = gr.Textbox(
                    placeholder="כתבו שאלה, למשל: באילו חברות עבדת?",
                    show_label=False,
                    container=False,
                    lines=1,
                    max_lines=4,
                    scale=6,
                    autofocus=True,
                )
                send = gr.Button("שליחה", variant="primary", scale=0, min_width=112)
                clear = gr.Button("שיחה חדשה", variant="secondary", scale=0, min_width=112)
        verdict = gr.HTML(VERDICT_IDLE, padding=False)
        gr.HTML(FOOTER_HTML, padding=False)

        staged_outputs = [msg, send, chatbot, pending, verdict]
        for trigger in (
            msg.submit(stage_question, [msg, chatbot], staged_outputs, queue=False),
            send.click(stage_question, [msg, chatbot], staged_outputs, queue=False),
            chatbot.example_select(stage_example, [chatbot], staged_outputs, queue=False),
        ):
            trigger.then(
                answer,
                [pending, chatbot, session],
                [chatbot, session, verdict],
                show_progress="minimal",
                show_progress_on=[chatbot],
            ).then(unlock, None, [msg, send], queue=False)

        reset_outputs = [chatbot, session, pending, verdict, msg]
        clear.click(reset, None, reset_outputs, queue=False)
        # The chat's own clear (trash) icon must also forget the model context.
        chatbot.clear(reset, None, reset_outputs, queue=False)
    return demo


def launch_app() -> None:
    create_demo().launch(server_name="127.0.0.1", theme=THEME, css=CSS)


if __name__ == "__main__":
    launch_app()
