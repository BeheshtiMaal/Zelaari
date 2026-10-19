"""Reconstruct plan changes from reviewed tool inputs, never editable metadata."""

import difflib
import json
import re
from pathlib import Path
from typing import Any

from planning.policy import matches, review_material
from planning.types import PlanStep, PlanSubmission
from tools.jail import resolve_virtual


def plan_review(
    root: Path,
    tool: str,
    args: dict[str, Any],
    before: dict[str, Any] | None,
    step_id: str | None,
) -> tuple[dict[str, Any] | None, str]:
    previous = PlanSubmission.model_validate(before) if before else None
    proposed: PlanSubmission | None = None
    if tool == "submit_plan":
        proposed = PlanSubmission.model_validate(args)
    elif previous and tool == "write_todos":
        steps: list[PlanStep] = []
        known = {step.id: step for step in previous.steps}
        for item in args.get("todos", []):
            if not isinstance(item, dict) or not isinstance(item.get("content"), str):
                raise ValueError("Invalid todo input")
            match = re.fullmatch(r"\[([a-zA-Z0-9_-]{1,64})\] (.+)", item["content"], re.DOTALL)
            if not match:
                raise ValueError("Todos must reference stable plan IDs")
            identity, title = match.groups()
            step = known.get(identity, PlanStep(id=identity, title=title))
            steps.append(PlanStep.model_validate({**step.model_dump(), "title": title}))
        proposed = PlanSubmission(steps=steps)
    elif previous and tool in {"write_file", "edit_file", "delete"} and step_id:
        path = args.get("file_path") or args.get("path")
        if isinstance(path, str):
            target = resolve_virtual(root, path, allow_protected=True)
            if not target.is_protected:
                proposed = previous.model_copy(deep=True)
                for step in proposed.steps:
                    if step.id == step_id and not any(
                        matches(target.relative, pattern) for pattern in step.expected_files
                    ):
                        step.expected_files.append(target.relative)
    if proposed is None:
        return None, ""
    before_text = json.dumps(before or {}, ensure_ascii=False, indent=2)
    after_text = json.dumps(proposed.model_dump(mode="json"), ensure_ascii=False, indent=2)
    diff = "".join(
        difflib.unified_diff(
            before_text.splitlines(keepends=True),
            after_text.splitlines(keepends=True),
            fromfile="accepted-plan.json",
            tofile="proposed-plan.json",
        )
    )
    return review_material(root, proposed), diff
