"""
Production-grade Hebrew Chat Interface for Assignment 1 (Part A: Actor).
Architectural visual polish pass:
- Enforces strict 8px spacing grid (8, 16, 24, 32px)
- Single primary typeface (Rubik) + monospace for code
- Bulletproof contrast: strict background-to-text pairing in both Light and Dark modes
- Eliminates any possibility of black-on-black or white-on-white text
- Standardized interactive states (default, hover, active, focus-visible)
- Strictly avoids unrequested gradients, heavy shadows, and decorative emoji clutter
"""

from pathlib import Path
import gradio as gr
from src.actor import chat_response
from src.config import DEFAULT_MODEL_NAME

# Static Assets
ASSETS_DIR = Path(__file__).resolve().parent / "assets"
USER_AVATAR_PATH = str(ASSETS_DIR / "user_avatar.svg")
BOT_AVATAR_PATH = str(ASSETS_DIR / "bot_avatar.svg")

# Design Tokens & Theme Configuration
CUSTOM_THEME = gr.themes.Soft(
    primary_hue="blue",
    neutral_hue="slate",
    font=[gr.themes.GoogleFont("Rubik"), "-apple-system", "BlinkMacSystemFont", "sans-serif"],
)

# Architectural Stylesheet adhering strictly to 8px grid and WCAG AA standards
CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;600;700&display=swap');

/* --- 1. CSS Variables for Light & Dark Mode --- */
:root {
    --space-1: 4px;
    --space-2: 8px;
    --space-3: 12px;
    --space-4: 16px;
    --space-5: 20px;
    --space-6: 24px;
    --space-8: 32px;

    --radius-sm: 6px;
    --radius-md: 8px;
    --radius-lg: 12px;
    --radius-full: 9999px;

    /* Light Mode Palette (Default) */
    --surface-bg: #f8fafc;
    --surface-card: #ffffff;
    --surface-subtle: #f1f5f9;
    --border-subtle: #e2e8f0;
    --border-strong: #cbd5e1;
    --border-focus: #2563eb;

    --text-primary: #0f172a;
    --text-secondary: #334155;
    --text-muted: #64748b;

    --input-bg: #ffffff;
    --input-text: #0f172a;
    --input-placeholder: #94a3b8;
    --input-border: #cbd5e1;

    --user-msg-bg: #2563eb;
    --user-msg-text: #ffffff;

    --bot-msg-bg: #ffffff;
    --bot-msg-border: #e2e8f0;
    --bot-msg-text: #0f172a;

    --chip-bg: #ffffff;
    --chip-border: #e2e8f0;
    --chip-text: #334155;
    --chip-hover-bg: #f1f5f9;
    --chip-hover-text: #0f172a;

    /* Accent strictly for Primary Action */
    --action-primary: #2563eb;
    --action-primary-hover: #1d4ed8;
    --action-primary-active: #1e40af;

    /* Status indicator */
    --status-active-dot: #16a34a;
    --status-active-bg: #f0fdf4;
    --status-active-border: #bbf7d0;
    --status-active-text: #166534;
}

/* Dark Mode Palette (Triggered automatically by browser/OS or Gradio .dark) */
.dark, :root.dark, body.dark, html.dark {
    --surface-bg: #090d16;
    --surface-card: #0f172a;
    --surface-subtle: #1e293b;
    --border-subtle: #1e293b;
    --border-strong: #334155;
    --border-focus: #3b82f6;

    --text-primary: #f8fafc;
    --text-secondary: #cbd5e1;
    --text-muted: #94a3b8;

    --input-bg: #0f172a;
    --input-text: #f8fafc;
    --input-placeholder: #64748b;
    --input-border: #334155;

    --user-msg-bg: #2563eb;
    --user-msg-text: #ffffff;

    --bot-msg-bg: #1e293b;
    --bot-msg-border: #334155;
    --bot-msg-text: #f8fafc;

    --chip-bg: #0f172a;
    --chip-border: #1e293b;
    --chip-text: #cbd5e1;
    --chip-hover-bg: #1e293b;
    --chip-hover-text: #ffffff;

    --status-active-bg: #052e16;
    --status-active-border: #14532d;
    --status-active-text: #86efac;
}

/* --- 2. Base Viewport & Direction --- */
body, html, .gradio-container {
    font-family: 'Rubik', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    direction: rtl !important;
    text-align: right !important;
    background-color: var(--surface-bg) !important;
    color: var(--text-primary) !important;
    margin: 0 !important;
    padding: 0 !important;
}

.gradio-container {
    max-width: 880px !important;
    margin: 0 auto !important;
    padding: var(--space-6) var(--space-4) !important;
}

/* --- 3. Header: Profile Showcase Card --- */
.profile-card {
    background-color: var(--surface-card) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-lg);
    padding: var(--space-5) var(--space-6);
    margin-bottom: var(--space-4);
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-4);
    flex-wrap: wrap;
}

.profile-info {
    display: flex;
    align-items: center;
    gap: var(--space-4);
}

.avatar-block {
    width: 48px;
    height: 48px;
    border-radius: var(--radius-md);
    background-color: #2563eb !important;
    color: #ffffff !important;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    font-weight: 600;
    letter-spacing: -0.02em;
    flex-shrink: 0;
}

.profile-titles h1 {
    margin: 0 0 var(--space-1) 0;
    font-size: 18px;
    line-height: 24px;
    font-weight: 600;
    color: var(--text-primary) !important;
}

.profile-titles p {
    margin: 0;
    font-size: 14px;
    line-height: 20px;
    color: var(--text-secondary) !important;
}

.profile-titles .affiliation-sub {
    font-size: 13px;
    line-height: 18px;
    color: var(--text-muted) !important;
    margin-top: var(--space-1);
}

.profile-meta {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-2);
}

.badge {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-1) var(--space-3);
    border-radius: var(--radius-full);
    font-size: 12px;
    line-height: 16px;
    font-weight: 500;
}

.badge-status {
    background-color: var(--status-active-bg) !important;
    border: 1px solid var(--status-active-border) !important;
    color: var(--status-active-text) !important;
}

.status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background-color: var(--status-active-dot);
}

.badge-model {
    background-color: var(--surface-subtle) !important;
    border: 1px solid var(--border-subtle) !important;
    color: var(--text-secondary) !important;
}

.badge-grounding {
    background-color: var(--surface-card) !important;
    border: 1px solid var(--border-subtle) !important;
    color: var(--text-muted) !important;
}

/* --- 4. Suggestion Chips Row --- */
.suggestions-container {
    margin-bottom: var(--space-4);
}

.suggestions-label {
    font-size: 12px;
    line-height: 16px;
    font-weight: 600;
    color: var(--text-muted) !important;
    margin-bottom: var(--space-2);
    letter-spacing: 0.01em;
}

.chips-grid {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
}

.chip-btn, button.chip-btn {
    background-color: var(--chip-bg) !important;
    border: 1px solid var(--chip-border) !important;
    border-radius: var(--radius-md) !important;
    padding: var(--space-2) var(--space-3) !important;
    font-size: 13px !important;
    line-height: 16px !important;
    font-weight: 500 !important;
    color: var(--chip-text) !important;
    cursor: pointer !important;
    transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease !important;
    box-shadow: none !important;
}

.chip-btn:hover, button.chip-btn:hover {
    background-color: var(--chip-hover-bg) !important;
    border-color: var(--border-strong) !important;
    color: var(--chip-hover-text) !important;
}

.chip-btn:active, button.chip-btn:active {
    background-color: var(--border-subtle) !important;
}

.chip-btn:focus-visible, button.chip-btn:focus-visible {
    outline: 2px solid var(--border-focus) !important;
    outline-offset: 2px !important;
}

/* --- 5. Chatbot Window & Strict Message Contrast --- */
.chat-window {
    background-color: var(--surface-card) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-lg) !important;
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05) !important;
    overflow: hidden !important;
}

.chat-window, .chat-window * {
    direction: rtl !important;
    text-align: right !important;
}

/* Sentence-level bidi isolation for mixed Hebrew/English */
.message, .bubble, .prose {
    font-size: 15px !important;
    line-height: 24px !important;
    direction: rtl !important;
    text-align: right !important;
    unicode-bidi: embed !important;
}

/* USER Message: ALWAYS Royal Blue with Pure White text (never dark on dark) */
[data-testid="user"], 
.message.user, 
.user-row .bubble, 
.user-row .message,
.user-row [class*="bubble"],
div[data-testid="user"] {
    background-color: var(--user-msg-bg) !important;
    color: var(--user-msg-text) !important;
    border-radius: var(--radius-lg) var(--radius-lg) var(--radius-sm) var(--radius-lg) !important;
}

[data-testid="user"] *, 
.message.user *, 
.user-row .bubble *, 
.user-row [class*="bubble"] *,
div[data-testid="user"] * {
    color: #ffffff !important;
}

/* BOT Message: Paired background and text (never light on light) */
[data-testid="bot"], 
.message.bot, 
.message.assistant, 
.bot-row .bubble, 
.bot-row .message,
.bot-row [class*="bubble"],
div[data-testid="bot"] {
    background-color: var(--bot-msg-bg) !important;
    border: 1px solid var(--bot-msg-border) !important;
    color: var(--bot-msg-text) !important;
    border-radius: var(--radius-lg) var(--radius-lg) var(--radius-lg) var(--radius-sm) !important;
}

[data-testid="bot"] *, 
.message.bot *, 
.message.assistant *, 
.bot-row .bubble *, 
.bot-row [class*="bubble"] *,
div[data-testid="bot"] * {
    color: var(--bot-msg-text) !important;
}

/* Technical Code Blocks */
code, pre code {
    direction: ltr !important;
    display: inline-block !important;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
    font-size: 13px !important;
    background-color: var(--surface-subtle) !important;
    border: 1px solid var(--border-subtle) !important;
    padding: 2px var(--space-1) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text-primary) !important;
}

/* Empty State Canvas */
.empty-state-wrap {
    padding: var(--space-8) var(--space-4);
    text-align: center;
    color: var(--text-muted) !important;
}

.empty-state-title {
    font-size: 16px;
    line-height: 24px;
    font-weight: 600;
    color: var(--text-primary) !important;
    margin: 0 0 var(--space-2) 0;
}

.empty-state-desc {
    font-size: 14px;
    line-height: 20px;
    color: var(--text-secondary) !important;
    max-width: 460px;
    margin: 0 auto;
}

/* --- 6. Bottom Action Bar (Input & Buttons) --- */
.action-row {
    margin-top: var(--space-4) !important;
    display: flex !important;
    align-items: center !important;
    gap: var(--space-2) !important;
}

.chat-input textarea,
.gradio-container textarea {
    border-radius: var(--radius-md) !important;
    border: 1px solid var(--input-border) !important;
    background-color: var(--input-bg) !important;
    color: var(--input-text) !important;
    font-size: 14px !important;
    line-height: 20px !important;
    padding: var(--space-3) var(--space-4) !important;
    direction: rtl !important;
    text-align: right !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
}

.chat-input textarea::placeholder,
.gradio-container textarea::placeholder {
    color: var(--input-placeholder) !important;
    opacity: 1 !important;
}

.chat-input textarea:focus,
.gradio-container textarea:focus {
    border-color: var(--border-focus) !important;
    box-shadow: 0 0 0 1px var(--border-focus) !important;
    outline: none !important;
}

.btn-primary, button.btn-primary {
    background-color: var(--action-primary) !important;
    color: #ffffff !important;
    border-radius: var(--radius-md) !important;
    font-size: 14px !important;
    line-height: 20px !important;
    font-weight: 500 !important;
    padding: var(--space-3) var(--space-5) !important;
    border: 1px solid transparent !important;
    cursor: pointer !important;
    transition: background-color 0.15s ease !important;
    box-shadow: none !important;
}

.btn-primary:hover, button.btn-primary:hover {
    background-color: var(--action-primary-hover) !important;
    color: #ffffff !important;
}

.btn-primary:active, button.btn-primary:active {
    background-color: var(--action-primary-active) !important;
    color: #ffffff !important;
}

.btn-primary:focus-visible, button.btn-primary:focus-visible {
    outline: 2px solid var(--border-focus) !important;
    outline-offset: 2px !important;
}

.btn-secondary, button.btn-secondary {
    background-color: var(--surface-card) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-secondary) !important;
    font-size: 14px !important;
    line-height: 20px !important;
    font-weight: 500 !important;
    padding: var(--space-3) var(--space-4) !important;
    cursor: pointer !important;
    transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease !important;
    box-shadow: none !important;
}

.btn-secondary:hover, button.btn-secondary:hover {
    background-color: var(--surface-subtle) !important;
    border-color: var(--border-strong) !important;
    color: var(--text-primary) !important;
}

.btn-secondary:active, button.btn-secondary:active {
    background-color: var(--border-subtle) !important;
}

.btn-secondary:focus-visible, button.btn-secondary:focus-visible {
    outline: 2px solid var(--border-focus) !important;
    outline-offset: 2px !important;
}

/* --- 7. Footer --- */
.footer-meta {
    text-align: center;
    font-size: 12px;
    line-height: 16px;
    color: var(--text-muted) !important;
    margin-top: var(--space-6);
}
"""

EMPTY_STATE_HTML = """
<div class="empty-state-wrap">
    <p class="empty-state-title">צ׳אט אישי עם אלון ברק</p>
    <p class="empty-state-desc">
        ניתן לשאול שאלות בנושאי השכלה, ניסיון מקצועי, מיומנויות ופרויקטים.<br>
        המענה מבוסס אך ורק על מקורות הרקע הרשמיים.
    </p>
</div>
"""

HEADER_HTML = f"""
<div class="profile-card">
    <div class="profile-info">
        <div class="avatar-block" aria-hidden="true">אב</div>
        <div class="profile-titles">
            <h1>אלון ברק</h1>
            <p>Senior AI Engineer &amp; Machine Learning Specialist</p>
            <p class="affiliation-sub">TechNova Solutions · מוסמך הטכניון ואוניברסיטת תל אביב</p>
        </div>
    </div>
    <div class="profile-meta">
        <span class="badge badge-status">
            <span class="status-dot"></span>
            <span>יוצר התשובה פעיל</span>
        </span>
        <span class="badge badge-grounding">ביסוס מקורות מלא</span>
        <span class="badge badge-model">מודל: {DEFAULT_MODEL_NAME}</span>
    </div>
</div>
"""

SUGGESTIONS = [
    ("השכלה ותזה", "ספר לי על ההשכלה האקדמית שלך ועל נושא התזה בטכניון."),
    ("ניסיון מקצועי ו-RAG", "מה הניסיון שלך בפיתוח ארכיטקטורות RAG בחברת TechNova?"),
    ("פרויקט DocuSense", "באילו טכנולוגיות השתמשת בפרויקט DocuSense AI ומה היו תוצאותיו?"),
    ("תחומי עניין ופנאי", "מהם התחביבים ותחומי העניין שלך בשעות הפנאי?"),
    ("בדיקת מידע חסר", "מה הציון שלך בבחינה הפסיכומטרית?"),
]


def create_demo() -> gr.Blocks:
    """Builds the polished, production-standard Hebrew chat interface."""
    with gr.Blocks(title="אלון ברק | צ׳אט אישי") as demo:
        # Header Section
        gr.HTML(HEADER_HTML)

        # Quick Suggestion Chips (8px grid container)
        with gr.Column(elem_classes=["suggestions-container"]):
            gr.HTML('<div class="suggestions-label">נושאים מומלצים לפתיחת שיחה:</div>')
            with gr.Row(elem_classes=["chips-grid"]):
                chip_buttons = []
                for label, prompt_text in SUGGESTIONS:
                    btn = gr.Button(label, elem_classes=["chip-btn"], size="sm")
                    chip_buttons.append((btn, prompt_text))

        # Main Chatbot Canvas
        chatbot = gr.Chatbot(
            rtl=True,
            height=480,
            show_label=False,
            placeholder=EMPTY_STATE_HTML,
            avatar_images=(USER_AVATAR_PATH, BOT_AVATAR_PATH),
            buttons=["copy"],
            elem_classes=["chat-window"],
        )

        # Bottom Action Bar
        with gr.Row(elem_classes=["action-row"]):
            msg_input = gr.Textbox(
                placeholder="הקלד כאן שאלה (לדוגמה: ספר לי על הפרויקטים שהובלת)...",
                show_label=False,
                container=False,
                scale=8,
                elem_classes=["chat-input"],
            )
            send_btn = gr.Button("שלח ←", variant="primary", scale=1, elem_classes=["btn-primary"])
            clear_btn = gr.Button("איפוס", variant="secondary", scale=1, elem_classes=["btn-secondary"])

        # Accessible Footer
        gr.HTML(
            '<div class="footer-meta">'
            'מטלה 1: מערכות בינה מלאכותית · חלק א׳: יוצר התשובה (Actor) עם יומן בדיקה נפרד'
            '</div>'
        )

        # Chat interaction logic
        def user_send(message: str, history: list):
            if not message or not message.strip():
                return "", history
            clean_msg = message.strip()
            history = history or []
            bot_reply = chat_response(clean_msg, history)
            updated_history = history + [
                {"role": "user", "content": clean_msg},
                {"role": "assistant", "content": bot_reply},
            ]
            return "", updated_history

        def clear_chat():
            return "", []

        # Event listeners
        msg_input.submit(user_send, [msg_input, chatbot], [msg_input, chatbot])
        send_btn.click(user_send, [msg_input, chatbot], [msg_input, chatbot])
        clear_btn.click(clear_chat, None, [msg_input, chatbot])

        # Suggestion chip interactions
        for btn, prompt_text in chip_buttons:
            def make_chip_handler(text):
                return lambda hist: user_send(text, hist)

            btn.click(make_chip_handler(prompt_text), [chatbot], [msg_input, chatbot])

    return demo


def launch_app():
    """Launch the app with standard production theme and design system stylesheet."""
    demo = create_demo()
    demo.launch(
        server_name="127.0.0.1",
        inbrowser=False,
        theme=CUSTOM_THEME,
        css=CUSTOM_CSS,
    )


if __name__ == "__main__":
    launch_app()
