"""
Part D: the five experiment scenarios.

Scenarios 1-4 use the real Actor and Critic. In scenario 4 a prepared flawed draft is
fed in as the first candidate; the Critic's decision and every revision still come
from the model. Scenario 5 is a control-flow check: a mock evaluator rejects every
attempt, so its result is reported apart from the model results.

For each scenario the run records the input, every attempt, the text shown to the
user, and whether the outcome matched the expectation (a list of explicit checks).
Output goes to a results directory:

- scenarios.json     the full record, model results and mock results in separate keys
- scenarios.md       the same record as a readable Hebrew report
- scenario_log.json  the raw inspection log of the run (one entry per question)
"""

import argparse
import json
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, NamedTuple

from openai import OpenAI

from src.actor import Actor
from src.config import PROJECT_ROOT, get_openai_client
from src.evaluator import Evaluator
from src.logger import InspectionLogger
from src.pipeline import EXHAUSTED_NOTICE, MAX_ATTEMPTS, TurnResult, handle_question
from src.schema import ChatTurn, Evaluation, RejectedDraft

DEFAULT_RESULTS_DIR = PROJECT_ROOT / "results"
REPORT_JSON = "scenarios.json"
REPORT_MD = "scenarios.md"
SCENARIO_LOG = "scenario_log.json"

MOCK_CRITIC_MODEL = "mock-always-reject (no model call)"
MOCK_FEEDBACK = "דחייה מדומה לבדיקת זרימת הבקרה: המעריך המדומה דוחה כל תשובה בלי לבדוק את תוכנה."

STATUS_LABELS = {
    "APPROVED": "אישור",
    "ATTEMPTS_EXHAUSTED": "מיצוי ניסיונות",
    "TECHNICAL_ERROR": "שגיאה טכנית",
}


# --- Stand-ins for the controlled scenarios ------------------------------------------


class InjectedFirstDraftActor(Actor):
    """Scenario 4: a prepared flawed draft as attempt 1, then real revisions."""

    def __init__(self, first_draft: str, client: OpenAI | None = None, model: str | None = None):
        super().__init__(client, model)
        self.first_draft = first_draft

    def generate(
        self,
        question: str,
        history: Sequence[ChatTurn] = (),
        rejected: RejectedDraft | None = None,
    ) -> str:
        if rejected is None:
            return self.first_draft
        return super().generate(question, history, rejected)


class AlwaysRejectEvaluator(Evaluator):
    """Scenario 5: a mock Critic that rejects every candidate without calling a model."""

    def __init__(self) -> None:
        super().__init__(model=MOCK_CRITIC_MODEL)

    def evaluate(
        self, question: str, candidate_response: str, history: Sequence[ChatTurn] = ()
    ) -> Evaluation:
        return Evaluation(is_acceptable=False, feedback=MOCK_FEEDBACK)


# --- Scenario definitions ------------------------------------------------------------


class Check(NamedTuple):
    description: str
    passed: bool


class SourceQuote(NamedTuple):
    """The detail in a background source that supports an approved answer."""

    file: str  # relative to the project root
    quote: str


@dataclass(frozen=True)
class Scenario:
    number: int
    title: str
    questions: tuple[str, ...]  # asked in order, in one conversation
    expected: str
    check: Callable[[Sequence[TurnResult]], list[Check]]
    injected_first_draft: str | None = None
    mock_evaluator: bool = False
    source: SourceQuote | None = None

    @property
    def id(self) -> str:
        return f"scenario-{self.number}"


def _approved(result: TurnResult) -> Check:
    return Check("הטיפול בשאלה הסתיים באישור (APPROVED)", result.approved)


def _mentions_google(text: str) -> bool:
    return "Google" in text or "גוגל" in text


def check_existing_info(results: Sequence[TurnResult]) -> list[Check]:
    (result,) = results
    return [
        _approved(result),
        Check("התשובה שהוצגה מציינת את הטכניון", result.approved and "טכניון" in result.message),
    ]


def check_follow_up(results: Sequence[TurnResult]) -> list[Check]:
    first, second = results
    return [
        Check(
            "הפנייה הראשונה אושרה ומציינת את אוניברסיטת תל אביב",
            first.approved and "תל אביב" in first.message,
        ),
        Check("שאלת ההמשך אושרה", second.approved),
        Check(
            "ההקשר נשמר: התשובה מציינת את ממוצע התואר הראשון (91) ולא את של השני (94)",
            second.approved and "91" in second.message and "94" not in second.message,
        ),
    ]


def check_missing_info(results: Sequence[TurnResult]) -> list[Check]:
    (result,) = results
    states_missing = any(word in result.message for word in ("אין", "אינו", "לא מופיע"))
    return [
        _approved(result),
        Check("התשובה מציינת שהמידע אינו במקורות", result.approved and states_missing),
        Check(
            "לא הומצא ציון: אין בתשובה מספר בן שלוש ספרות",
            result.approved and not re.search(r"\d{3}", result.message),
        ),
    ]


def check_rejection_and_fix(results: Sequence[TurnResult]) -> list[Check]:
    (result,) = results
    first = result.attempts[0].evaluation if result.attempts else None
    rejected = first is not None and not first.is_acceptable
    return [
        Check("הטיוטה הפגומה (ניסיון 1) נדחתה על ידי המעריך", rejected),
        Check(
            "המשוב מצביע על הטענה שהומצאה (Google)",
            first is not None and rejected and _mentions_google(first.feedback),
        ),
        Check(
            "גרסה מתוקנת הוערכה מחדש ואושרה",
            result.approved and len(result.attempts) >= 2,
        ),
        Check(
            "התשובה שהוצגה אינה כוללת את העובדה שהומצאה ומציינת מעסיק מהמקורות",
            result.approved
            and not _mentions_google(result.message)
            and ("DataPulse" in result.message or "InnoSoft" in result.message),
        ),
    ]


def check_exhaustion(results: Sequence[TurnResult]) -> list[Check]:
    (result,) = results
    all_rejected = all(a.evaluation is not None and not a.approved for a in result.attempts)
    drafts = [a.candidate for a in result.attempts]
    return [
        Check(
            "הטיפול בשאלה הסתיים במיצוי ניסיונות (ATTEMPTS_EXHAUSTED)",
            result.status == "ATTEMPTS_EXHAUSTED",
        ),
        Check(
            f"בוצעו בדיוק {MAX_ATTEMPTS} ניסיונות וכולם נדחו",
            len(result.attempts) == MAX_ATTEMPTS and all_rejected,
        ),
        Check(
            "הוצגה הודעת הסיום ולא אחת מהטיוטות שנדחו",
            result.message == EXHAUSTED_NOTICE and result.message not in drafts,
        ),
    ]


FLAWED_DRAFT = "לפני TechNova עבדתי שבע שנים כמהנדס ראשי ב-Google בקליפורניה."

SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        number=1,
        title="שאלה על מידע קיים",
        questions=("באיזה מוסד עשית את התואר השני שלך?",),
        expected="תשובה מאושרת שמציינת את הטכניון, עם הפניה לפרט התומך בה במקור.",
        check=check_existing_info,
        source=SourceQuote(
            "data/linkedin_profile.txt",
            "תואר שני (M.Sc.) במדעי המחשב - התמחות בבינה מלאכותית | הטכניון",
        ),
    ),
    Scenario(
        number=2,
        title="שאלת המשך",
        questions=("איפה למדת לתואר הראשון?", "ובאיזה ממוצע סיימת אותו?"),
        expected=(
            'שתי פניות באותה שיחה. השנייה נשענת על הקודמת ("אותו"), ולכן התשובה '
            "צריכה לציין את ממוצע התואר השני (94) ולא את ממוצע התואר הראשון (91)."
        ),
        check=check_follow_up,
    ),
    Scenario(
        number=3,
        title="פרט שאינו במקורות",
        questions=("מה הציון שלך בבחינה הפסיכומטרית?",),
        expected="תשובה מאושרת שמציינת שהמידע אינו במקורות, בלי להמציא ציון.",
        check=check_missing_info,
    ),
    Scenario(
        number=4,
        title="דחייה ושיפור",
        questions=("באילו חברות עבדת לפני TechNova?",),
        expected=(
            "טיוטת המבחן הפגומה (עבודה ב-Google, שאינה במקורות) נדחית עם משוב מנומק, "
            "היוצר מפיק גרסה מתוקנת, והיא מוערכת מחדש ומאושרת."
        ),
        check=check_rejection_and_fix,
        injected_first_draft=FLAWED_DRAFT,
    ),
    Scenario(
        number=5,
        title="מיצוי הניסיונות",
        questions=("מה הניסיון שלך בפיתוח ארכיטקטורות RAG?",),
        expected=(
            f"{MAX_ATTEMPTS} ניסיונות שנדחו, עצירה אחרי הניסיון האחרון והודעת סיום, "
            "בלי להציג אף טיוטה שנדחתה."
        ),
        check=check_exhaustion,
        mock_evaluator=True,
    ),
)


# --- Running -------------------------------------------------------------------------


def locate_quote(source: SourceQuote) -> dict[str, Any]:
    """Find the supporting quote in its source file (line is None if it is not there)."""
    lines = (PROJECT_ROOT / source.file).read_text(encoding="utf-8").splitlines()
    line = next((n for n, text in enumerate(lines, start=1) if source.quote in text), None)
    return {"file": source.file, "line": line, "quote": source.quote}


def run_scenario(
    scenario: Scenario, logger: InspectionLogger, client: OpenAI | None = None
) -> dict[str, Any]:
    """Run one scenario as its own conversation and return its record."""
    if scenario.injected_first_draft is None:
        actor = Actor(client)
    else:
        actor = InjectedFirstDraftActor(scenario.injected_first_draft, client)
    evaluator = AlwaysRejectEvaluator() if scenario.mock_evaluator else Evaluator(client)

    history: list[ChatTurn] = []
    results: list[TurnResult] = []
    for turn_index, question in enumerate(scenario.questions, start=1):
        result = handle_question(
            question,
            history,
            actor=actor,
            evaluator=evaluator,
            logger=logger,
            session_id=scenario.id,
            turn_index=turn_index,
            scenario_id=scenario.id,
        )
        results.append(result)
        if result.approved:  # as in the chat: only delivered answers become context
            history = [
                *history,
                {"role": "user", "content": question},
                {"role": "assistant", "content": result.message},
            ]

    checks = scenario.check(results)
    source = locate_quote(scenario.source) if scenario.source else None
    if source is not None:
        checks.append(Check("הפרט התומך נמצא בקובץ המקור", source["line"] is not None))

    return {
        "scenario_id": scenario.id,
        "number": scenario.number,
        "title": scenario.title,
        "result_kind": "mock_control_flow" if scenario.mock_evaluator else "llm",
        "actor_model": actor.model,
        "critic_model": evaluator.model,
        "expected": scenario.expected,
        "injected_first_draft": scenario.injected_first_draft,
        "source_reference": source,
        "turns": [
            {
                "turn_index": turn_index,
                "question": question,
                "status": result.status,
                "shown_to_user": result.message,
                "attempts": [attempt.to_log() for attempt in result.attempts],
            }
            for turn_index, (question, result) in enumerate(
                zip(scenario.questions, results, strict=True), start=1
            )
        ],
        "checks": [check._asdict() for check in checks],
        "matched_expectation": all(check.passed for check in checks),
    }


def run_all(
    out_dir: Path = DEFAULT_RESULTS_DIR,
    client: OpenAI | None = None,
    scenarios: Sequence[Scenario] = SCENARIOS,
) -> dict[str, Any]:
    """Run the scenarios, write the three result files into out_dir, return the report."""
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / SCENARIO_LOG
    log_path.unlink(missing_ok=True)  # every run writes a fresh log of its own questions
    logger = InspectionLogger(log_path)

    records = [run_scenario(scenario, logger, client) for scenario in scenarios]
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "max_attempts": MAX_ATTEMPTS,
        "llm_results": [r for r in records if r["result_kind"] == "llm"],
        "mock_results": [r for r in records if r["result_kind"] == "mock_control_flow"],
    }
    (out_dir / REPORT_JSON).write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (out_dir / REPORT_MD).write_text(render_report(report), encoding="utf-8")
    return report


def all_records(report: dict[str, Any]) -> list[dict[str, Any]]:
    return [*report["llm_results"], *report["mock_results"]]


# --- Report --------------------------------------------------------------------------


def _quote(text: str) -> str:
    return "\n".join(f"> {line}" if line else ">" for line in text.splitlines())


def _yes_no(value: bool) -> str:
    return "כן" if value else "לא"


def _render_attempt(attempt: dict[str, Any], record: dict[str, Any]) -> list[str]:
    if not attempt["evaluation_completed"]:
        decision = "שגיאה טכנית, ההערכה לא הושלמה"
    elif attempt["is_acceptable"]:
        decision = "אושר"
    else:
        decision = "נדחה"

    notes = []
    if attempt["attempt_number"] == 1 and record["injected_first_draft"]:
        notes.append("טיוטת מבחן פגומה שהוזנה ידנית, לא פלט של המודל")
    if record["result_kind"] == "mock_control_flow":
        notes.append("החלטה של מעריך מדומה")
    suffix = f" ({'; '.join(notes)})" if notes else ""

    lines = [f"#### ניסיון {attempt['attempt_number']}: {decision}{suffix}", ""]
    if attempt["candidate_response"]:
        lines += [_quote(attempt["candidate_response"]), ""]
    if attempt["feedback"]:
        lines += [f"**משוב המעריך:** {attempt['feedback']}", ""]
    if attempt["technical_error"]:
        error = attempt["technical_error"]
        lines += [f"**שגיאה טכנית** (שלב `{error['stage']}`): {error['message']}", ""]
    return lines


def _render_scenario(record: dict[str, Any]) -> list[str]:
    lines = [
        f"### תרחיש {record['number']}: {record['title']}",
        "",
        f"**ציפייה:** {record['expected']}",
        "",
    ]
    for turn in record["turns"]:
        lines += [f"**פנייה {turn['turn_index']} (קלט):** {turn['question']}", ""]
        for attempt in turn["attempts"]:
            lines += _render_attempt(attempt, record)
        status = STATUS_LABELS[turn["status"]]
        lines += [f"**הוצג למשתמש** (מצב סיום: {status}):", "", _quote(turn["shown_to_user"]), ""]

    source = record["source_reference"]
    if source:
        where = f"שורה {source['line']}" if source["line"] else "לא נמצא בקובץ"
        lines += [f"**הפרט התומך במקור:** `{source['file']}`, {where}:", ""]
        lines += [_quote(source["quote"]), ""]

    lines += ["**בדיקות:**", ""]
    lines += [
        f"- {'עבר' if check['passed'] else 'נכשל'}: {check['description']}"
        for check in record["checks"]
    ]
    matched = _yes_no(record["matched_expectation"])
    lines += ["", f"**ההתנהגות בפועל תאמה את הציפייה: {matched}**", ""]
    return lines


def _summary_row(record: dict[str, Any]) -> str:
    kind = "מודל שפה" if record["result_kind"] == "llm" else "בדיקה מדומה"
    statuses = ", ".join(STATUS_LABELS[turn["status"]] for turn in record["turns"])
    attempts = ", ".join(str(len(turn["attempts"])) for turn in record["turns"])
    matched = _yes_no(record["matched_expectation"])
    name = f"{record['number']}. {record['title']}"
    return f"| {name} | {kind} | {statuses} | {attempts} | {matched} |"


def render_report(report: dict[str, Any]) -> str:
    """The Hebrew Markdown report: model results and the mock result in separate sections."""
    lines = [
        '<div dir="rtl">',
        "",
        "# תוצאות חלק ד׳: חמשת התרחישים",
        "",
        f"הופק ב-{report['generated_at']} בהרצת `python run_scenarios.py`. "
        f"לכל שאלה יש לכל היותר {report['max_attempts']} ניסיונות יצירה.",
        "",
        'העמודה "תאם את הציפייה" נקבעת לפי הבדיקות האוטומטיות המפורטות בכל תרחיש. '
        "בתרחיש עם שתי פניות, מצב הסיום ומספר הניסיונות מופיעים לכל פנייה בנפרד.",
        "",
        "| תרחיש | סוג התוצאה | מצב סיום | ניסיונות | תאם את הציפייה |",
        "|---|---|---|---|---|",
        *[_summary_row(record) for record in all_records(report)],
        "",
    ]

    sections = (
        (
            "תוצאות שהתקבלו ממודל שפה",
            "ההחלטות והמשוב בתרחישים אלה הם פלט של מודל השפה. בתרחיש 4 רק הטיוטה "
            "הראשונה הוזנה ידנית; ההערכה והתיקון שאחריה בוצעו על ידי המודל.",
            report["llm_results"],
        ),
        (
            "בדיקה מדומה של זרימת הבקרה",
            "תוצאות אלה אינן הערכה של מודל שפה. מעריך מדומה מחזיר דחייה בכל ניסיון, "
            "כדי לבדוק שהלולאה נעצרת במגבלת הניסיונות. הטיוטות עצמן הופקו על ידי היוצר.",
            report["mock_results"],
        ),
    )
    for title, intro, records in sections:
        if not records:
            continue
        models = sorted({(r["actor_model"], r["critic_model"]) for r in records})
        lines += [f"## {title}", "", intro, ""]
        lines += [f"יוצר התשובה: `{actor}`. מעריך התשובות: `{critic}`." for actor, critic in models]
        lines += [""]
        for record in records:
            lines += _render_scenario(record)

    lines += ["</div>", ""]
    return "\n".join(lines)


# --- Command line --------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the five Part D scenarios.")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_RESULTS_DIR,
        help="directory for the result files (default: results/)",
    )
    args = parser.parse_args(argv)

    try:
        get_openai_client()  # fail before overwriting earlier results if the key is missing
    except ValueError as error:
        print(error)
        return 2

    report = run_all(args.out)
    for record in all_records(report):
        statuses = ", ".join(turn["status"] for turn in record["turns"])
        attempts = ", ".join(str(len(turn["attempts"])) for turn in record["turns"])
        matched = "yes" if record["matched_expectation"] else "NO"
        print(
            f"{record['scenario_id']}  {record['result_kind']:<17}  status: {statuses}  "
            f"attempts: {attempts}  matched expectation: {matched}"
        )
    print(f"Results written to {args.out}")
    return 0 if all(r["matched_expectation"] for r in all_records(report)) else 1
