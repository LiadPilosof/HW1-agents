"""
Design system for the Gradio UI.

One palette per mode (LIGHT / DARK) is the single source of truth: it feeds both the
Gradio theme variables (which style built-in components such as chat bubbles, inputs
and buttons) and the CSS custom properties used by the app's own HTML (header,
badges, the verdict alert).
"""

import inspect

from gradio.themes import Base, GoogleFont

LIGHT = {
    "bg": "#f4f6f5",
    "surface": "#ffffff",
    "surface-2": "#f7f9f8",
    "surface-hover": "#eef2f0",
    "border": "#e2e7e5",
    "border-strong": "#c8d1ce",
    "text": "#142028",
    "text-2": "#46535d",
    "text-3": "#64707a",
    "accent": "#1b6b57",
    "accent-hover": "#155a49",
    "accent-contrast": "#ffffff",
    "accent-soft": "#e7f2ee",
    "accent-soft-border": "#bfdcd1",
    "accent-text": "#155a49",
    "ring": "rgba(27, 107, 87, 0.28)",
    "success": "#1b6b57",
    "success-soft": "#e9f4f0",
    "success-border": "#bfdcd1",
    "danger": "#b03a26",
    "danger-soft": "#fbeeea",
    "danger-border": "#f0c9bf",
    "warning": "#8a5300",
    "warning-soft": "#fbf3e3",
    "warning-border": "#ecd6a8",
    "shadow-sm": "0 1px 2px rgba(16, 24, 32, 0.05)",
    "shadow-md": "0 1px 2px rgba(16, 24, 32, 0.04), 0 6px 16px -4px rgba(16, 24, 32, 0.10)",
    "shadow-lg": "0 1px 3px rgba(16, 24, 32, 0.04), 0 16px 40px -16px rgba(16, 24, 32, 0.16)",
}

DARK = {
    "bg": "#0d1215",
    "surface": "#141b20",
    "surface-2": "#19222a",
    "surface-hover": "#1f2a33",
    "border": "#253039",
    "border-strong": "#34424d",
    "text": "#e8edf0",
    "text-2": "#b3bec6",
    "text-3": "#8d99a3",
    "accent": "#4fbf9c",
    "accent-hover": "#63cba9",
    "accent-contrast": "#06231b",
    "accent-soft": "#11291f",
    "accent-soft-border": "#1f4a3b",
    "accent-text": "#7fd6b8",
    "ring": "rgba(79, 191, 156, 0.35)",
    "success": "#63cba9",
    "success-soft": "#10241d",
    "success-border": "#1f4a3b",
    "danger": "#f08d76",
    "danger-soft": "#2a1712",
    "danger-border": "#5a2c22",
    "warning": "#e6b45a",
    "warning-soft": "#2a2212",
    "warning-border": "#5a4520",
    "shadow-sm": "0 1px 2px rgba(0, 0, 0, 0.30)",
    "shadow-md": "0 1px 2px rgba(0, 0, 0, 0.30), 0 8px 20px -6px rgba(0, 0, 0, 0.45)",
    "shadow-lg": "0 1px 3px rgba(0, 0, 0, 0.30), 0 20px 48px -18px rgba(0, 0, 0, 0.60)",
}

TRANSITION = (
    "background-color 160ms ease, border-color 160ms ease, color 160ms ease, "
    "box-shadow 160ms ease, transform 160ms ease"
)


_THEME_VARIABLES = set(inspect.signature(Base.set).parameters)


def _modes(**mapping: str) -> dict[str, str]:
    """Map Gradio theme variables to palette keys, adding *_dark where Gradio supports it."""
    values: dict[str, str] = {}
    for variable, key in mapping.items():
        values[variable] = LIGHT[key]
        if f"{variable}_dark" in _THEME_VARIABLES:
            values[f"{variable}_dark"] = DARK[key]
    return values


THEME = Base(
    primary_hue="emerald",
    neutral_hue="slate",
    font=[GoogleFont("IBM Plex Sans Hebrew"), "Arial", "sans-serif"],
    font_mono=[GoogleFont("IBM Plex Mono"), "ui-monospace", "monospace"],
).set(
    **_modes(
        body_background_fill="bg",
        body_text_color="text",
        body_text_color_subdued="text-3",
        background_fill_primary="surface",
        background_fill_secondary="surface-2",
        border_color_primary="border",
        border_color_accent="accent",
        border_color_accent_subdued="accent-soft-border",
        color_accent="accent",
        color_accent_soft="accent-soft",
        link_text_color="accent-text",
        block_background_fill="surface",
        block_border_color="border",
        input_background_fill="surface-2",
        input_background_fill_hover="surface",
        input_background_fill_focus="surface",
        input_border_color="border",
        input_border_color_hover="border-strong",
        input_border_color_focus="accent",
        input_placeholder_color="text-3",
        loader_color="accent",
        button_primary_background_fill="accent",
        button_primary_background_fill_hover="accent-hover",
        button_primary_border_color="accent",
        button_primary_border_color_hover="accent-hover",
        button_primary_text_color="accent-contrast",
        button_primary_text_color_hover="accent-contrast",
        button_secondary_background_fill="surface",
        button_secondary_background_fill_hover="surface-hover",
        button_secondary_border_color="border-strong",
        button_secondary_border_color_hover="border-strong",
        button_secondary_text_color="text",
        button_secondary_text_color_hover="text",
        shadow_drop="shadow-sm",
        button_primary_shadow="shadow-sm",
        button_primary_shadow_hover="shadow-md",
        button_secondary_shadow="shadow-sm",
        button_secondary_shadow_hover="shadow-md",
    ),
    input_shadow_focus=f"0 0 0 3px {LIGHT['ring']}",
    input_shadow_focus_dark=f"0 0 0 3px {DARK['ring']}",
    button_primary_shadow_active="none",
    button_secondary_shadow_active="none",
    button_transform_hover="none",
    button_transform_active="translateY(1px)",
    button_transition=TRANSITION,
    block_shadow="none",
    block_radius="12px",
    input_radius="10px",
    button_large_radius="10px",
    button_medium_radius="10px",
    button_small_radius="8px",
    chatbot_text_size="15px",
    body_text_size="15px",
)


def _custom_properties(palette: dict[str, str]) -> str:
    return "\n".join(f"  --{name}: {value};" for name, value in palette.items())


_COMPONENT_CSS = """
:root { --dur: 160ms; }

/* ---------- Page ---------- */
.gradio-container {
  direction: rtl;
  width: 100% !important;
  max-width: 800px !important;
  margin: 0 auto !important;
  padding: 0 !important;
  color: var(--text);
}
.gradio-container .main { padding: 40px 16px 24px !important; }
.gradio-container .contain { width: 100%; }
/* The app's own HTML blocks align flush with the chat panel. */
.gradio-container .html-container { padding: 0 !important; }
.app-header, .verdict, .footer-note { direction: rtl; }
.gradio-container button,
.gradio-container textarea,
.gradio-container .example,
.verdict summary,
.badge {
  transition: background-color var(--dur) ease, border-color var(--dur) ease,
    color var(--dur) ease, box-shadow var(--dur) ease, transform var(--dur) ease;
}
.gradio-container button:focus-visible,
.gradio-container .example:focus-visible,
.verdict summary:focus-visible {
  outline: none !important;
  box-shadow: 0 0 0 3px var(--ring) !important;
}
.gradio-container button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none !important;
  transform: none !important;
}
.gradio-container svg.icon {
  width: 16px; height: 16px; flex: none;
  fill: none; stroke: currentColor; stroke-width: 2;
  stroke-linecap: round; stroke-linejoin: round;
}

/* ---------- Header ---------- */
.app-header {
  display: flex; align-items: center; justify-content: space-between;
  gap: 16px; flex-wrap: wrap; margin-bottom: 20px;
}
.identity { display: flex; align-items: center; gap: 14px; min-width: 0; }
.monogram {
  width: 48px; height: 48px; flex: none; border-radius: 50%;
  display: grid; place-items: center;
  background: var(--accent); color: var(--accent-contrast);
  font-size: 17px; font-weight: 600;
  box-shadow: 0 0 0 4px var(--accent-soft);
}
.identity h1 {
  margin: 0; font-size: 24px; line-height: 32px; font-weight: 600;
  letter-spacing: -0.015em; color: var(--text);
}
.identity p { margin: 2px 0 0; font-size: 14px; line-height: 20px; color: var(--text-2); }

/* ---------- Badges ---------- */
.badges { display: flex; gap: 8px; flex-wrap: wrap; }
.badge {
  display: inline-flex; align-items: center; gap: 6px;
  height: 28px; padding: 0 12px; border-radius: 999px;
  font-size: 13px; line-height: 16px; font-weight: 500;
  border: 1px solid var(--border); background: var(--surface); color: var(--text-2);
}
.badge-accent {
  background: var(--accent-soft); border-color: var(--accent-soft-border); color: var(--accent-text);
}

/* ---------- Chat panel ---------- */
.chat-panel {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 16px !important;
  box-shadow: var(--shadow-lg);
  padding: 0 !important;
  gap: 0 !important;
  overflow: hidden;
}
.chat-window, .chat-window > .wrapper {
  border: none !important; border-radius: 0 !important;
  box-shadow: none !important; background: transparent !important;
}
.chat-window .message { line-height: 1.7; }
.chat-window .message-row .message { border-radius: 14px; }
.chat-window .icon-button-wrapper button {
  border-radius: 8px !important; color: var(--text-3) !important;
  background: transparent !important; border: none !important;
}
.chat-window .message-buttons .icon-button-wrapper {
  border: none !important; background: transparent !important; box-shadow: none !important;
}
.chat-window .icon-button-wrapper button:hover {
  background: var(--surface-hover); color: var(--text);
}

.chat-window .icon-button-wrapper.top-panel {
  top: 10px !important; right: 10px !important; left: auto !important;
  padding: 2px !important; border-radius: 10px !important;
  background: var(--surface) !important; border: 1px solid var(--border) !important;
  box-shadow: var(--shadow-sm) !important;
}

/* Empty state: heading + example cards */
.chat-window .placeholder-content { justify-content: center; gap: 4px; }
.chat-window .placeholder-content > * { flex: none !important; }
.chat-window .placeholder { height: auto !important; }
/* Keep Gradio's typing indicator, drop its "processing | 0.9s" timer text. */
.chat-window .progress-text, .chat-window .meta-text, .chat-window .meta-text-center { display: none !important; }
.chat-window .placeholder {
  text-align: center; padding: 8px 24px 0; color: var(--text-2);
  font-size: 14px; line-height: 22px;
}
.chat-window .placeholder strong {
  display: block; margin-bottom: 4px;
  font-size: 18px; line-height: 28px; font-weight: 600; color: var(--text);
}
.chat-window .examples {
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)) !important;
  gap: 10px !important; padding: 16px 24px 8px !important; margin: 0 auto !important;
  width: 100%; max-width: 640px;
}
.chat-window .example {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
  padding: 14px 16px !important;
  box-shadow: var(--shadow-sm);
  text-align: start;
}
.chat-window .example:hover {
  background: var(--accent-soft) !important;
  border-color: var(--accent-soft-border) !important;
  box-shadow: var(--shadow-md);
  transform: translateY(-1px) !important;
}
.chat-window .example:active { transform: translateY(0) !important; box-shadow: var(--shadow-sm); }
.chat-window .example-text { font-size: 14px; line-height: 21px; color: var(--text); }

/* Composer */
.composer {
  border-top: 1px solid var(--border);
  background: var(--surface);
  padding: 12px !important;
  gap: 8px !important;
  align-items: flex-end !important;
}
.composer textarea { font-size: 15px !important; line-height: 22px !important; }
.composer button { min-width: 112px; height: 44px; font-size: 15px; font-weight: 500; white-space: nowrap; }

/* ---------- Verdict alert ---------- */
.verdict {
  --tone: var(--text-2); --tone-soft: var(--surface); --tone-border: var(--border);
  display: flex; gap: 12px; align-items: flex-start;
  margin-top: 16px; padding: 14px 16px;
  border-radius: 12px; border: 1px solid var(--tone-border);
  background: var(--tone-soft); box-shadow: var(--shadow-sm);
  animation: verdict-in 180ms ease;
}
.verdict.approved { --tone: var(--success); --tone-soft: var(--success-soft); --tone-border: var(--success-border); }
.verdict.exhausted { --tone: var(--danger); --tone-soft: var(--danger-soft); --tone-border: var(--danger-border); }
.verdict.error { --tone: var(--warning); --tone-soft: var(--warning-soft); --tone-border: var(--warning-border); }
.verdict.pending { --tone: var(--accent); }
.verdict-icon {
  flex: none; width: 28px; height: 28px; border-radius: 50%;
  display: grid; place-items: center;
  color: var(--tone); background: var(--surface); border: 1px solid var(--tone-border);
}
.verdict.pending .verdict-icon svg { animation: spin 0.9s linear infinite; }
.verdict-body { flex: 1; min-width: 0; }
.verdict-title { margin: 0; font-size: 15px; line-height: 22px; font-weight: 600; color: var(--tone); }
.verdict.idle .verdict-title { color: var(--text); }
.verdict-text { margin: 2px 0 0; font-size: 14px; line-height: 21px; color: var(--text-2); }
.verdict .skeleton {
  height: 8px; margin-top: 10px; border-radius: 4px;
  background-color: var(--border-strong) !important;
  animation: skeleton-pulse 1.2s ease-in-out infinite;
}
.verdict .skeleton.short { width: 55%; }
.verdict details { margin-top: 8px; }
.verdict summary {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 8px; margin-inline-start: -8px; border-radius: 8px;
  font-size: 13px; line-height: 20px; font-weight: 500; color: var(--tone);
  cursor: pointer; list-style: none;
}
.verdict summary::-webkit-details-marker { display: none; }
.verdict summary:hover { background: var(--surface); }
.verdict summary .icon { transition: transform var(--dur) ease; }
.verdict details[open] summary .icon { transform: rotate(180deg); }
.feedback {
  margin: 8px 0 0; padding: 10px 12px; border-radius: 8px;
  background: var(--surface); border: 1px solid var(--tone-border);
  font-size: 14px; line-height: 22px; color: var(--text); white-space: pre-wrap;
}

.attempts { list-style: none; margin: 8px 0 0; padding: 0; display: grid; gap: 8px; }
.attempt { display: block; --mark: var(--text-3); padding-inline-start: 12px; border-inline-start: 3px solid var(--mark); }
/* Gradio's prose makes <p> inside <li> inline; keep heading and feedback stacked. */
.verdict .attempt > p { display: block !important; }
.attempt.approved { --mark: var(--success); }
.attempt.rejected { --mark: var(--danger); }
.attempt.error { --mark: var(--warning); }
.attempt-head { margin: 0; font-size: 13px; line-height: 20px; font-weight: 600; color: var(--mark); }
.attempt .feedback { margin-top: 4px; }
.feedback.technical {
  direction: ltr; text-align: left; font-family: var(--font-mono);
  font-size: 12.5px; line-height: 20px; color: var(--text-2);
}
.footer-note { margin: 16px 0 0; font-size: 12px; line-height: 18px; color: var(--text-3); text-align: center; }

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes skeleton-pulse { 0%, 100% { opacity: 0.45; } 50% { opacity: 1; } }
@keyframes verdict-in { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }

/* ---------- Small screens ---------- */
@media (max-width: 600px) {
  .gradio-container .main { padding: 20px 16px 16px !important; }
  .identity h1 { font-size: 21px; line-height: 28px; }
  .monogram { width: 42px; height: 42px; font-size: 15px; }
  .chat-panel { border-radius: 12px !important; }
  .chat-window .examples { grid-template-columns: 1fr !important; padding: 12px !important; }
  .composer { flex-wrap: wrap !important; }
  .composer > :first-child { flex: 1 1 100% !important; }
  .composer button { min-width: 0; flex: 1 1 0 !important; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important; animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
"""

# Gradio has no *_dark variant for these two theme variables, so override them here.
_DARK_ONLY_OVERRIDES = f"  --color-accent: {DARK['accent']};\n  --shadow-drop: {DARK['shadow-sm']};"

CSS = (
    f":root {{\n{_custom_properties(LIGHT)}\n}}\n"
    f".dark {{\n{_custom_properties(DARK)}\n{_DARK_ONLY_OVERRIDES}\n}}\n"
    f"{_COMPONENT_CSS}"
)
