"""Adapt the installed todo schema without trusting model-owned plan identity."""

import re
from datetime import datetime
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field

from planning.types import PlanRecord, PlanStep, PlanSubmission, StepProgress, StepStatus

_CONTENT = re.compile(r"^\[([a-zA-Z0-9_-]{1,64})\] (.+)$", re.DOTALL)


class TodoInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    todos: list[dict[str, Any]] = Field(min_length=1, max_length=64)


def adapt_todos(
    plan: PlanRecord,
    arguments: dict[str, Any],
    now: datetime,
    *,
    running_children: set[str] | None = None,
) -> tuple[PlanSubmission, list[StepProgress]]:
    """Structural changes become proposals; callers must gate before storing either output."""
    values = TodoInput.model_validate(arguments)
    existing = {step.id: step for step in plan.submission.steps}
    previous = {item.step_id: item for item in plan.progress}
    steps: list[PlanStep] = []
    progress: list[StepProgress] = []
    for value in values.todos:
        if set(value) != {"content", "status"}:
            raise ValueError("Todos require only content and status")
        content = value["content"]
        if not isinstance(content, str) or not (match := _CONTENT.fullmatch(content)):
            raise ValueError("Todo content must be '[stable_step_id] title'")
        identity, title = match.groups()
        status = value["status"]
        if not isinstance(status, str) or status not in {"pending", "in_progress", "completed"}:
            raise ValueError("Use the installed todo status enum")
        step = existing.get(identity, PlanStep(id=identity, title=title)).model_copy(
            update={"title": title}
        )
        # Re-validate bounds after model_copy, which intentionally does not validate.
        steps.append(PlanStep.model_validate(step.model_dump()))
        before = previous.get(identity, StepProgress(step_id=identity))
        if before.status in {"completed", "failed"} and status != before.status:
            raise ValueError("Terminal step history cannot be rewritten")
        if before.status == "pending" and status == "completed":
            raise ValueError("Start a step before completing it")
        if before.status == "in_progress" and status == "pending":
            raise ValueError("An active step cannot return to pending")
        if status == "completed" and identity in (running_children or set()):
            raise ValueError("Wait for all running children before completing their parent")
        progress.append(
            StepProgress(
                step_id=identity,
                status=cast(StepStatus, status),
                started_at=before.started_at or (now if status == "in_progress" else None),
                ended_at=before.ended_at or (now if status == "completed" else None),
            )
        )
    if sum(item.status == "in_progress" for item in progress) > 1:
        raise ValueError("Only one parent step can be active")
    if any(
        item.status == "completed" and item.step_id not in {s.id for s in steps}
        for item in plan.progress
    ):
        raise ValueError("Completed history cannot be dropped")
    return PlanSubmission(steps=steps), progress


def active_step(plan: PlanRecord) -> PlanStep | None:
    active = [item.step_id for item in plan.progress if item.status == "in_progress"]
    if len(active) != 1:
        return None
    return next((step for step in plan.submission.steps if step.id == active[0]), None)
