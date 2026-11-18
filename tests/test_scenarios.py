"""Part D: the five-scenario runner (offline, scripted model replies)."""

import json

import pytest

from src.pipeline import EXHAUSTED_NOTICE, MAX_ATTEMPTS
from src.prompts import build_revision_request
from src.scenarios import (
    FLAWED_DRAFT,
    MOCK_CRITIC_MODEL,
    MOCK_FEEDBACK,
    REPORT_JSON,
    REPORT_MD,
    SCENARIO_LOG,
    SCENARIOS,
    AlwaysRejectEvaluator,
    InjectedFirstDraftActor,
    all_records,
    locate_quote,
    main,
    run_all,
)
from src.schema import RejectedDraft
from tests.fakes import completion, evaluation_json

APPROVE = evaluation_json(True, "נתמך במקורות")
REJECT_GOOGLE = evaluation_json(
    False, "העבודה ב-Google אינה במקורות; יש לציין DataPulse ו-InnoSoft."
)

# Actor replies in call order. Scenario 4's first draft is injected, so the Actor is
# called there only for the revision.
ACTOR_REPLIES = [
    "עשיתי את התואר השני בטכניון.",  # 1
    "למדתי לתואר הראשון באוניברסיטת תל אביב.",  # 2, turn 1
    "סיימתי אותו בממוצע 91.",  # 2, turn 2
    "הציון הפסיכומטרי אינו מופיע במקורות שלי.",  # 3
    "לפני TechNova עבדתי ב-DataPulse וב-InnoSoft.",  # 4, revision
    "טיוטה א",  # 5
    "טיוטה ב",
    "טיוטה ג",
]
CRITIC_REPLIES = [APPROVE, APPROVE, APPROVE, APPROVE, REJECT_GOOGLE, APPROVE]


def script(fake_client, actor_replies=ACTOR_REPLIES, critic_replies=CRITIC_REPLIES):
    fake_client.chat.completions.create.side_effect = [completion(x) for x in actor_replies]
    fake_client.chat.completions.parse.side_effect = [completion(x) for x in critic_replies]


def actor_calls(fake_client):
    return [c.kwargs["messages"] for c in fake_client.chat.completions.create.call_args_list]


@pytest.fixture
def report(fake_client, tmp_path):
    script(fake_client)
    return run_all(tmp_path, client=fake_client)


def by_number(report):
    return {record["number"]: record for record in all_records(report)}


def test_all_five_scenarios_run_and_match(report):
    records = by_number(report)
    assert sorted(records) == [1, 2, 3, 4, 5]
    assert all(r["matched_expectation"] for r in records.values()), records
    assert [t["status"] for t in records[2]["turns"]] == ["APPROVED", "APPROVED"]
    assert records[5]["turns"][0]["status"] == "ATTEMPTS_EXHAUSTED"


def test_model_results_and_mock_results_are_reported_separately(report):
    assert [r["number"] for r in report["llm_results"]] == [1, 2, 3, 4]
    assert [r["number"] for r in report["mock_results"]] == [5]
    assert report["mock_results"][0]["result_kind"] == "mock_control_flow"
    assert report["mock_results"][0]["critic_model"] == MOCK_CRITIC_MODEL
    assert all(r["critic_model"] != MOCK_CRITIC_MODEL for r in report["llm_results"])


def test_scenario_1_points_at_the_supporting_line_in_the_source(report):
    source = by_number(report)[1]["source_reference"]
    assert source["file"] == "data/linkedin_profile.txt"
    assert isinstance(source["line"], int) and "הטכניון" in source["quote"]


def test_scenario_2_follow_up_receives_the_previous_answer(fake_client, report):
    follow_up = actor_calls(fake_client)[2]
    assert [m["content"] for m in follow_up[1:]] == [
        "איפה למדת לתואר הראשון?",
        "למדתי לתואר הראשון באוניברסיטת תל אביב.",
        "ובאיזה ממוצע סיימת אותו?",
    ]
    # Each scenario is its own conversation: scenario 3 starts without history.
    assert len(actor_calls(fake_client)[3]) == 2


def test_scenario_4_rejects_the_injected_draft_then_approves_the_revision(fake_client, report):
    record = by_number(report)[4]
    first, second = record["turns"][0]["attempts"]
    assert record["injected_first_draft"] == FLAWED_DRAFT == first["candidate_response"]
    assert first["is_acceptable"] is False and "Google" in first["feedback"]
    assert second["is_acceptable"] is True
    assert record["turns"][0]["shown_to_user"] == "לפני TechNova עבדתי ב-DataPulse וב-InnoSoft."
    # The revision call carried the rejected draft and the Critic's feedback.
    revision = actor_calls(fake_client)[4]
    assert revision[-2] == {"role": "assistant", "content": FLAWED_DRAFT}
    assert revision[-1]["content"] == build_revision_request(first["feedback"])


def test_scenario_5_stops_after_three_mock_rejections(fake_client, report):
    turn = by_number(report)[5]["turns"][0]
    assert [a["candidate_response"] for a in turn["attempts"]] == ["טיוטה א", "טיוטה ב", "טיוטה ג"]
    assert [a["is_acceptable"] for a in turn["attempts"]] == [False] * MAX_ATTEMPTS
    assert {a["feedback"] for a in turn["attempts"]} == {MOCK_FEEDBACK}
    assert turn["shown_to_user"] == EXHAUSTED_NOTICE
    # The mock Critic made no model call: only scenarios 1-4 reached the Critic model.
    assert fake_client.chat.completions.parse.call_count == len(CRITIC_REPLIES)


def test_result_files_are_written(report, tmp_path):
    assert json.loads((tmp_path / REPORT_JSON).read_text(encoding="utf-8")) == report
    log = json.loads((tmp_path / SCENARIO_LOG).read_text(encoding="utf-8"))
    assert [(e["scenario_id"], e["turn_index"]) for e in log] == [
        ("scenario-1", 1),
        ("scenario-2", 1),
        ("scenario-2", 2),
        ("scenario-3", 1),
        ("scenario-4", 1),
        ("scenario-5", 1),
    ]
    markdown = (tmp_path / REPORT_MD).read_text(encoding="utf-8")
    llm_section = markdown.index("## תוצאות שהתקבלו ממודל שפה")
    mock_section = markdown.index("## בדיקה מדומה של זרימת הבקרה")
    assert llm_section < markdown.index("### תרחיש 4") < mock_section
    assert mock_section < markdown.index("### תרחיש 5")
    assert "טיוטת מבחן פגומה שהוזנה ידנית" in markdown
    assert EXHAUSTED_NOTICE in markdown


def test_a_rerun_replaces_the_scenario_log(fake_client, tmp_path):
    for _ in range(2):
        script(fake_client)
        run_all(tmp_path, client=fake_client)
    assert len(json.loads((tmp_path / SCENARIO_LOG).read_text(encoding="utf-8"))) == 6


def test_critic_approving_the_flawed_draft_is_recorded_as_a_mismatch(fake_client, tmp_path):
    """Part D: if the Critic approves the flawed draft, the failure must be documented."""
    actor_replies = [r for r in ACTOR_REPLIES if "DataPulse" not in r]  # no revision happens
    script(fake_client, actor_replies, [APPROVE] * 5)
    record = by_number(run_all(tmp_path, client=fake_client))[4]

    assert record["matched_expectation"] is False
    assert record["turns"][0]["shown_to_user"] == FLAWED_DRAFT
    failed = [c["description"] for c in record["checks"] if not c["passed"]]
    assert any("נדחתה" in description for description in failed)
    assert "תאמה את הציפייה: לא" in (tmp_path / REPORT_MD).read_text(encoding="utf-8")


def test_technical_error_is_reported_not_treated_as_a_match(fake_client, tmp_path):
    fake_client.chat.completions.create.side_effect = ConnectionError("down")
    record = by_number(run_all(tmp_path, client=fake_client, scenarios=SCENARIOS[:1]))[1]
    assert record["turns"][0]["status"] == "TECHNICAL_ERROR"
    assert record["matched_expectation"] is False
    assert "שגיאה טכנית" in (tmp_path / REPORT_MD).read_text(encoding="utf-8")


def test_injected_first_draft_actor_only_replaces_the_first_attempt(fake_client):
    fake_client.chat.completions.create.return_value = completion("גרסה מתוקנת")
    actor = InjectedFirstDraftActor("טיוטה פגומה", fake_client)
    assert actor.generate("שאלה") == "טיוטה פגומה"
    assert not fake_client.chat.completions.create.called
    assert actor.generate("שאלה", (), RejectedDraft("טיוטה פגומה", "משוב")) == "גרסה מתוקנת"


def test_always_reject_evaluator_returns_a_valid_rejection_without_a_model_call():
    evaluator = AlwaysRejectEvaluator()
    evaluation = evaluator.evaluate("שאלה", "כל תשובה")
    assert evaluation.is_acceptable is False and evaluation.feedback == MOCK_FEEDBACK
    assert evaluator.model == MOCK_CRITIC_MODEL
    assert evaluator._client is None  # no client was ever created


def test_every_scenario_source_quote_exists_in_its_file():
    for scenario in SCENARIOS:
        if scenario.source:
            assert locate_quote(scenario.source)["line"] is not None, scenario.id


def test_main_stops_before_running_when_the_api_key_is_missing(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert main(["--out", str(tmp_path)]) == 2
    assert "OPENAI_API_KEY" in capsys.readouterr().out
    assert list(tmp_path.iterdir()) == []
