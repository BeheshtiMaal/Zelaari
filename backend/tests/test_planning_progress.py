"""Stable todo identity and lifecycle, independent of presentation titles."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from planning.policy import digest, file_scope
from planning.progress import active_step, adapt_todos
from planning.types import PlanningSettings, PlanRecord, PlanStep, PlanSubmission, StepProgress


def plan(tmp_path: Path) -> PlanRecord:
    submission = PlanSubmission(
        steps=[PlanStep(id="first", title="Read"), PlanStep(id="next", title="Edit")]
    )
    return PlanRecord(
        run_id="run",
        plan_id="plan",
        revision=digest(submission.model_dump()),
        baseline_ids=["first", "next"],
        submission=submission,
        progress=[StepProgress(step_id=step.id) for step in submission.steps],
        adoption="automatic",
        file_scope=file_scope(tmp_path, submission),
        settings=PlanningSettings(),
    )


def test_todo_identity_and_persisted_timestamps(tmp_path: Path) -> None:
    current = plan(tmp_path)
    now = datetime.now(UTC)
    _, progress = adapt_todos(
        current,
        {
            "todos": [
                {"content": "[first] Read", "status": "in_progress"},
                {"content": "[next] Edit", "status": "pending"},
            ]
        },
        now,
    )
    current.progress = progress
    assert active_step(current) == current.submission.steps[0]
    assert progress[0].started_at == now
    _, next_progress = adapt_todos(
        current,
        {
            "todos": [
                {"content": "[first] Read", "status": "completed"},
                {"content": "[next] Edit", "status": "in_progress"},
            ]
        },
        now,
    )
    assert next_progress[0].started_at == now
    assert next_progress[0].ended_at == now
    assert next_progress[1].started_at == now


@pytest.mark.parametrize(
    "todos",
    [
        [{"content": "Read", "status": "in_progress"}],
        [{"content": "[first] Read", "status": "failed"}],
        [{"content": "[first] Read", "status": "completed"}],
        [
            {"content": "[first] Read", "status": "in_progress"},
            {"content": "[next] Edit", "status": "in_progress"},
        ],
        [{"content": "[first] Read", "status": "pending", "id": "forged"}],
    ],
)
def test_ambiguous_forged_and_invalid_transitions(
    tmp_path: Path, todos: list[dict[str, str]]
) -> None:
    with pytest.raises(ValueError):
        adapt_todos(plan(tmp_path), {"todos": todos}, datetime.now(UTC))


def test_running_children_and_completed_history_cannot_be_erased(tmp_path: Path) -> None:
    current = plan(tmp_path)
    current.progress[0].status = "in_progress"
    with pytest.raises(ValueError, match="running children"):
        adapt_todos(
            current,
            {"todos": [{"content": "[first] Read", "status": "completed"}]},
            datetime.now(UTC),
            running_children={"first"},
        )
    current.progress[0].status = "completed"
    with pytest.raises(ValueError, match="history"):
        adapt_todos(
            current, {"todos": [{"content": "[next] Edit", "status": "pending"}]}, datetime.now(UTC)
        )


def test_structure_changes_return_proposals_not_silent_replacement(tmp_path: Path) -> None:
    current = plan(tmp_path)
    proposed, _ = adapt_todos(
        current,
        {"todos": [{"content": "[added] New task", "status": "pending"}]},
        datetime.now(UTC),
    )
    assert proposed.steps[0].id == "added"
    assert current.submission.steps[0].id == "first"
