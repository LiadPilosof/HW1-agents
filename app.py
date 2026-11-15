"""
Modern & Clean Hebrew Gradio Chat Interface for Part A (Actor - Response Generator).
Designed with professional SaaS aesthetics, native RTL layout, and zero generic clutter.
"""

import gradio as gr
from src.actor import chat_response
from src.config import DEFAULT_MODEL_NAME

# Sleek typography and custom modern theme
CUSTOM_THEME = gr.themes.Soft(
    primary_hue="blue",
    neutral_hue="slate",
    font=[gr.themes.GoogleFont("Rubik"), "-apple-system", "BlinkMacSystemFont", "sans-serif"],
)

# Custom CSS for modern, premium appearance (no generic AI-slop look)
CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Rubik:wght@300;400;500;600;700&display=swap');

:root {
    --primary: #2563eb;
    --primary-hover: #1d4ed8;
    --bg-main: #f8fafc;
    --card-bg: #ffffff;
    --border: #e2e8f0;
    --text-primary: #0f172a;
    --text-secondary: #475569;
    --text-muted: #64748b;
}

body, html, .gradio-container {
    font-family: 'Rubik', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    direction: rtl !important;
    text-align: right !important;
    background-color: var(--bg-main) !important;
    color: var(--text-primary) !important;
}

/* Wrapper alignment and maximum readability width */
.gradio-container {
    max-width: 920px !important;
    margin: 0 auto !important;
    padding: 1.5rem 1rem !important;
}

/* Profile Showcase Header Card */
.profile-card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.5rem 1.75rem;
    margin-bottom: 1.25rem;
    box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.04);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1.5rem;
    flex-wrap: wrap;
}

.profile-info {
    display: flex;
    align-items: center;
    gap: 1.25rem;
}

.avatar-circle {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
    color: #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.3rem;
    font-weight: 700;
    box-shadow: 0 4px 14px rgba(37, 99, 235, 0.28);
    flex-shrink: 0;
    letter-spacing: -0.5px;
}

.profile-titles h2 {
    margin: 0 0 0.25rem 0;
    font-size: 1.35rem;
    font-weight: 700;
    color: var(--text-primary);
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.verified-badge {
    background: #e0f2fe;
    color: #0284c7;
    font-size: 0.75rem;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
}

.profile-titles p {
    margin: 0;
    font-size: 0.925rem;
    color: var(--text-secondary);
    line-height: 1.4;
}

.affiliation-sub {
    font-size: 0.825rem !important;
    color: var(--text-muted) !important;
    margin-top: 0.2rem !important;
}

.profile-meta {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.4rem;
}

.badge-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.28rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.785rem;
    font-weight: 500;
}

.badge-status {
    background: #ecfdf5;
    color: #065f46;
    border: 1px solid #a7f3d0;
}

.status-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background-color: #10b981;
    box-shadow: 0 0 0 2px #d1fae5;
}

.badge-grounding {
    background: #f8fafc;
    color: #475569;
    border: 1px solid #e2e8f0;
}

.badge-model {
    background: #eff6ff;
    color: #1e40af;
    border: 1px solid #bfdbfe;
}

/* Quick Suggestion Chips */
.suggestions-wrap {
    margin-bottom: 1rem;
}

.suggestions-header {
    font-size: 0.825rem;
    font-weight: 600;
    color: var(--text-muted);
    margin-bottom: 0.5rem;
}

.chips-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
}

.chip-btn {
    background: #ffffff !important;
    border: 1px solid var(--border) !important;
    border-radius: 9999px !important;
    padding: 0.4rem 0.85rem !important;
    font-size: 0.825rem !important;
    font-weight: 500 !important;
    color: var(--text-secondary) !important;
    cursor: pointer !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03) !important;
}

.chip-btn:hover {
    background: #f1f5f9 !important;
    border-color: #cbd5e1 !important;
    color: var(--text-primary) !important;
    transform: translateY(-1px);
    box-shadow: 0 3px 6px rgba(15, 23, 42, 0.05) !important;
}

/* Chatbot Window Styling */
.chat-window {
    border-radius: 16px !important;
    border: 1px solid var(--border) !important;
    background: var(--card-bg) !important;
    box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.04) !important;
    overflow: hidden !important;
}

/* Input Area Row */
.input-row {
    margin-top: 1rem !important;
    display: flex !important;
    align-items: center !important;
    gap: 0.6rem !important;
}

.chat-input textarea {
    border-radius: 14px !important;
    border: 1px solid #cbd5e1 !important;
    background: #ffffff !important;
    font-family: inherit !important;
    font-size: 0.95rem !important;
    padding: 0.85rem 1.1rem !important;
    line-height: 1.5 !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}

.chat-input textarea:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12) !important;
    outline: none !important;
}

.send-btn {
    background: var(--primary) !important;
    color: #ffffff !important;
    border-radius: 14px !important;
    font-weight: 600 !important;
    padding: 0.75rem 1.5rem !important;
    border: none !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.25) !important;
}

.send-btn:hover {
    background: var(--primary-hover) !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35) !important;
}

.clear-btn {
    background: #ffffff !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    color: var(--text-muted) !important;
    font-weight: 500 !important;
    padding: 0.75rem 1.1rem !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
}

.clear-btn:hover {
    background: #f8fafc !important;
    color: var(--text-primary) !important;
    border-color: #cbd5e1 !important;
}

/* Discreet Footer */
.footer-note {
    text-align: center;
    font-size: 0.785rem;
    color: #94a3b8;
    margin-top: 1.25rem;
    line-height: 1.5;
}
"""

EMPTY_CHAT_PLACEHOLDER = """
<div style="text-align: center; padding: 3rem 1.5rem; color: #64748b;">
    <div style="width: 52px; height: 52px; margin: 0 auto 1.25rem; background: #eff6ff; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.6rem; color: #2563eb; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.12);">💬</div>
    <h3 style="margin: 0 0 0.5rem 0; font-size: 1.25rem; font-weight: 700; color: #0f172a;">שלום! אני הנציג הדיגיטלי של אלון ברק</h3>
    <p style="margin: 0 auto; max-width: 520px; font-size: 0.925rem; line-height: 1.6; color: #475569;">
        אני כאן כדי לשוחח עמכם ולענות על שאלות אודות ההשכלה, הניסיון התעסוקתי, המיומנויות והפרויקטים שלי.<br>
        כל תשובותיי מבוססות <b>אך ורק על מקורות הרקע הרשמיים</b>.
    </p>
</div>
"""

HEADER_HTML = f"""
<div class="profile-card">
    <div class="profile-info">
        <div class="avatar-circle">אב</div>
        <div class="profile-titles">
            <h2>אלון ברק <span class="verified-badge" title="מאומת מול מקורות הרקע">✓</span></h2>
            <p>Senior AI Engineer &amp; Machine Learning Specialist</p>
            <p class="affiliation-sub">TechNova Solutions · מוסמך הטכניון ואונ׳ תל אביב</p>
        </div>
    </div>
    <div class="profile-meta">
        <div class="badge-pill badge-status">
            <span class="status-dot"></span>
            <span>נציג פעיל (Actor)</span>
        </div>
        <div class="badge-pill badge-grounding">
            <span>🔒 ביסוס קפדני במקורות</span>
        </div>
        <div class="badge-pill badge-model">
            <span>מודל: <b>{DEFAULT_MODEL_NAME}</b></span>
        </div>
    </div>
</div>
"""

SUGGESTIONS = [
    ("🎓 השכלה ותזה בטכניון", "ספר לי על ההשכלה האקדמית שלך ועל נושא התזה בטכניון."),
    ("💼 ניסיון ב-RAG וב-TechNova", "מה הניסיון שלך בפיתוח ארכיטקטורות RAG בחברת TechNova?"),
    ("🚀 פרויקט DocuSense AI", "באילו טכנולוגיות השתמשת בפרויקט DocuSense AI ומה היו תוצאותיו?"),
    ("🏃 תחביבים בשעות הפנאי", "מהם התחביבים ותחומי העניין שלך בשעות הפנאי?"),
    ("❓ ציון פסיכומטרי (בדיקת מידע חסר)", "מה הציון שלך בבחינה הפסיכומטרית?"),
]


def create_demo() -> gr.Blocks:
    """Builds a modern, polished Hebrew chat interface with custom blocks."""
    with gr.Blocks(title="אלון ברק | Digital Twin (Actor)") as demo:
        # Header profile card
        gr.HTML(HEADER_HTML)

        # Quick Suggestion Chips
        with gr.Column(elem_classes=["suggestions-wrap"]):
            gr.HTML('<div class="suggestions-header">💡 שאלות נפוצות להתחלה מהירה:</div>')
            with gr.Row(elem_classes=["chips-row"]):
                chip_buttons = []
                for label, prompt_text in SUGGESTIONS:
                    btn = gr.Button(label, elem_classes=["chip-btn"], size="sm")
                    chip_buttons.append((btn, prompt_text))

        # Main Chatbot Container
        chatbot = gr.Chatbot(
            rtl=True,
            height=480,
            show_label=False,
            placeholder=EMPTY_CHAT_PLACEHOLDER,
            elem_classes=["chat-window"],
        )

        # Bottom Input Bar
        with gr.Row(elem_classes=["input-row"]):
            msg_input = gr.Textbox(
                placeholder="הקלד כאן שאלה (לדוגמה: ספר לי על הפרויקטים שהובלת)...",
                show_label=False,
                container=False,
                scale=8,
                elem_classes=["chat-input"],
            )
            send_btn = gr.Button("שלח ↵", variant="primary", scale=1, elem_classes=["send-btn"])
            clear_btn = gr.Button("נקה שיחה", variant="secondary", scale=1, elem_classes=["clear-btn"])

        # Footer note
        gr.HTML(
            '<div class="footer-note">'
            'מטלה 1: מערכות בינה מלאכותית · חלק א׳: יוצר התשובה (Actor) עם יומן בדיקה נפרד (inspection log)'
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

        # Wire events
        msg_input.submit(user_send, [msg_input, chatbot], [msg_input, chatbot])
        send_btn.click(user_send, [msg_input, chatbot], [msg_input, chatbot])
        clear_btn.click(clear_chat, None, [msg_input, chatbot])

        # Wire suggestion chips
        for btn, prompt_text in chip_buttons:
            # When clicking a chip, populate and send automatically
            def make_chip_handler(text):
                return lambda hist: user_send(text, hist)

            btn.click(make_chip_handler(prompt_text), [chatbot], [msg_input, chatbot])

    return demo


def launch_app():
    """Launch the app with modern theme and custom styling."""
    demo = create_demo()
    demo.launch(
        server_name="127.0.0.1",
        inbrowser=False,
        theme=CUSTOM_THEME,
        css=CUSTOM_CSS,
    )


if __name__ == "__main__":
    launch_app()
