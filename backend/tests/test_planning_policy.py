"""Thresholds, concrete targets, configuration revisions and cumulative deviation."""

from pathlib import Path

import pytest

from permissions.review import prepare_review
from permissions.types import ApprovalRequest
from planning.policy import (
    deviation_reasons,
    digest,
    file_scope,
    initial_reasons,
    load_settings,
    merged_settings,
)
from planning.types import PlanningSettings, PlanRecord, PlanStep, PlanSubmission, StepProgress


def submission(count: int = 3, files: list[str] | None = None) -> PlanSubmission:
    return PlanSubmission(
        steps=[
            PlanStep(id=f"s{index}", title=f"Step {index}", expected_files=files or [])
            for index in range(count)
        ]
    )


@pytest.mark.parametrize("mode", ["ask", "read-only", "auto"])
@pytest.mark.parametrize("steps,files,review", [(3, 3, False), (4, 3, True), (3, 4, True)])
def test_initial_threshold_matrix(
    tmp_path: Path, mode: str, steps: int, files: int, review: bool
) -> None:
    value = submission(steps, [f"file{n}.txt" for n in range(files)])
    scope = file_scope(tmp_path, value)
    assert len(scope.known_files) == files
    assert bool(initial_reasons(tmp_path, value, scope, PlanningSettings(), mode)) == (
        review and mode != "auto"
    )


def test_configurable_thresholds_and_fixed_risk(tmp_path: Path) -> None:
    value = submission(1)
    settings = PlanningSettings(step_threshold=2, file_threshold=1)
    assert initial_reasons(tmp_path, value, file_scope(tmp_path, value), settings, "ask") == []
    value.steps[0].verify_command = "git reset --hard"
    assert initial_reasons(tmp_path, value, file_scope(tmp_path, value), settings, "ask") == [
        "high_risk"
    ]
    value.steps[0].verify_command = None
    value.steps[0].high_risk = True
    assert initial_reasons(tmp_path, value, file_scope(tmp_path, value), settings, "read-only") == [
        "high_risk"
    ]


def test_turning_the_plan_gate_off_stops_every_review(tmp_path: Path) -> None:
    # The gate is the switch the person sees; off has to mean off, including for a high-risk
    # step, because the alternative is a switch that only sometimes switches.
    value = submission(8, [f"file{n}.txt" for n in range(5)])
    value.steps[0].high_risk = True
    scope = file_scope(tmp_path, value)
    assert initial_reasons(tmp_path, value, scope, PlanningSettings(), "ask") != []
    off = PlanningSettings(plan_gate=False)
    for mode in ("ask", "read-only", "auto"):
        assert initial_reasons(tmp_path, value, scope, off, mode) == []
    # Defaults keep the gate on, so no existing workspace changes behaviour.
    assert PlanningSettings().plan_gate is True


def test_distinct_existing_matches_literals_and_unknown(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    for name in ("a.py", "b.py"):
        (tmp_path / "src" / name).write_text("source", encoding="utf-8")
    value = submission(2, ["src/*.py", "src/a.py", "new.py"])
    scope = file_scope(tmp_path, value)
    assert scope.known_files == ["new.py", "src/a.py", "src/b.py"]
    assert not scope.uncertain
    unknown = file_scope(tmp_path, submission(1, ["missing/**/*.py"]))
    assert unknown.uncertain
    assert initial_reasons(tmp_path, submission(1), unknown, PlanningSettings(), "ask") == [
        "uncertain_file_scope"
    ]


def test_config_preserves_unknown_keys_and_refuses_malformed(tmp_path: Path) -> None:
    storage = tmp_path / ".harness"
    storage.mkdir()
    path = storage / "config.json"
    assert load_settings(tmp_path)[0] == PlanningSettings()
    path.write_text('{"future": {"enabled": true}}', encoding="utf-8")
    before = path.read_bytes()
    content = merged_settings(tmp_path, PlanningSettings(step_threshold=5))
    assert '"future"' in content
    assert path.read_bytes() == before
    path.write_text('{"planning": {"step_threshold": false}}', encoding="utf-8")
    with pytest.raises(ValueError):
        merged_settings(tmp_path, PlanningSettings())
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(ValueError):
        merged_settings(tmp_path, PlanningSettings())
    assert path.read_text(encoding="utf-8") == "{broken"


def test_review_is_bound_to_config_and_file_expansion(tmp_path: Path) -> None:
    (tmp_path / "a.py").touch()
    value = submission(1, ["*.py"])
    request = ApprovalRequest(
        approval_id="plan",
        run_id="run",
        kind="tool",
        tool="submit_plan",
        args=value.model_dump(mode="json"),
    )
    before = prepare_review(tmp_path, request)
    (tmp_path / "b.py").touch()
    after = prepare_review(tmp_path, request)
    assert before.revision != after.revision
    (tmp_path / ".harness").mkdir()
    (tmp_path / ".harness" / "config.json").write_text(
        '{"planning": {"step_threshold": 6}}', encoding="utf-8"
    )
    assert prepare_review(tmp_path, request).revision != after.revision


def record(tmp_path: Path) -> PlanRecord:
    value = submission(2, ["src/*.py"])
    return PlanRecord(
        run_id="run",
        plan_id="plan",
        revision=digest(value.model_dump()),
        baseline_ids=[step.id for step in value.steps],
        submission=value,
        progress=[StepProgress(step_id=step.id) for step in value.steps],
        adoption="automatic",
        file_scope=file_scope(tmp_path, value),
        settings=PlanningSettings(),
    )


def test_cumulative_third_addition_and_dropped_step(tmp_path: Path) -> None:
    previous = record(tmp_path)
    for index in range(2, 5):
        next_plan = previous.submission.model_copy(deep=True)
        next_plan.steps.append(PlanStep(id=f"s{index}", title="Added"))
        assert deviation_reasons(previous, next_plan) == (["added_steps"] if index == 4 else [])
        previous.submission = next_plan
    next_plan = previous.submission.model_copy(deep=True)
    next_plan.steps.pop(0)
    assert "dropped_step" in deviation_reasons(previous, next_plan)


def test_reorder_rename_cannot_hide_scope_or_risk_changes(tmp_path: Path) -> None:
    previous = record(tmp_path)
    proposed = previous.submission.model_copy(deep=True)
    proposed.steps.reverse()
    proposed.steps[0].title = "Renamed"
    assert deviation_reasons(previous, proposed) == []
    proposed.steps[0].expected_files = ["**/*"]
    assert deviation_reasons(previous, proposed) == ["changed_scope_or_risk"]
    previous.settings.deviation_gate = False
    assert deviation_reasons(previous, proposed) == []
