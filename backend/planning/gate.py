"""Plan decisions used by the existing pre-tool human barrier."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import ToolCall

from permissions.types import PermissionOutcome, RiskAssessment
from planning.policy import (
    deviation_reasons,
    digest,
    file_scope,
    initial_reasons,
    load_settings,
    matches,
    review_material,
)
from planning.progress import active_step, adapt_todos
from planning.types import PlanRecord, PlanSubmission, StepProgress
from tools.jail import resolve_virtual

EFFECTS = frozenset(
    {"write_file", "edit_file", "delete", "run_command", "git_switch", "worktree_create"}
)


class PlanGate:
    def __init__(self, root: Path, run_id: str, mode: str) -> None:
        self.root, self.run_id, self.mode = root, run_id, mode

    def proposal(self, call: ToolCall, previous: PlanRecord | None) -> PlanSubmission | None:
        if call["name"] == "submit_plan":
            return PlanSubmission.model_validate(call["args"])
        if previous is None:
            return None
        if call["name"] == "write_todos":
            proposed, _ = adapt_todos(previous, call["args"], datetime.now(UTC))
            return proposed
        if call["name"] in {"write_file", "edit_file", "delete"}:
            path = call["args"].get("file_path") or call["args"].get("path")
            if not isinstance(path, str):
                raise ValueError("Missing mutation target")
            resolved = resolve_virtual(self.root, path, allow_protected=True)
            if resolved.is_protected:
                # Ordinary permission review and the dispatch jail still protect engine files.
                # A scope deviation can never adopt these into agent-writable scope.
                return None
            target = resolved.relative
            active = active_step(previous)
            if active and not any(matches(target, glob) for glob in active.expected_files):
                proposed = previous.submission.model_copy(deep=True)
                for step in proposed.steps:
                    if step.id == active.id:
                        step.expected_files.append(target)
                return proposed
        return None

    def classify(
        self, call: ToolCall, previous: PlanRecord | None, ordinary: PermissionOutcome
    ) -> PermissionOutcome:
        if call["name"] not in EFFECTS | {"submit_plan", "write_todos"}:
            return ordinary
        try:
            settings, _, _ = load_settings(self.root)
            if call["name"] in EFFECTS:
                if ordinary.action == "deny":
                    return ordinary
                if previous is None or previous.adoption not in {"automatic", "approved"}:
                    return PermissionOutcome(action="deny", reason="Submit an accepted plan first")
                if active_step(previous) is None:
                    return PermissionOutcome(
                        action="deny", reason="Start one accepted plan step first"
                    )
            proposed = self.proposal(call, previous)
            if proposed is None:
                return ordinary
            material = review_material(self.root, proposed)
            if previous is None:
                reasons = initial_reasons(
                    self.root, proposed, file_scope(self.root, proposed), settings, self.mode
                )
            else:
                # Refresh settings each turn so old records cannot freeze the toggle.
                effective = previous.model_copy(update={"settings": settings})
                reasons = deviation_reasons(effective, proposed)
            if reasons:
                return PermissionOutcome(
                    action="ask",
                    reason="Plan review: " + ", ".join(reasons),
                    risk=RiskAssessment(
                        level="high" if "high_risk" in reasons else ordinary.risk.level,
                        reasons=reasons if "high_risk" in reasons else ordinary.risk.reasons,
                    ),
                )
            if call["name"] == "submit_plan":
                return PermissionOutcome(action="allow", reason="Plan automatically adopted")
            # Evaluate material now even for automatic plans: jail/config errors fail closed.
            assert material
            return ordinary
        except (OSError, ValueError):
            return PermissionOutcome(
                action="deny", reason="Invalid plan, progress or workspace config"
            )

    def adopt(
        self,
        call: ToolCall,
        previous: PlanRecord | None,
        *,
        reviewed: bool,
        running_children: set[str] | None = None,
    ) -> PlanRecord | None:
        proposed = self.proposal(call, previous)
        if proposed is None:
            return previous
        if previous and any(
            item.status == "completed" and item.step_id not in {step.id for step in proposed.steps}
            for item in previous.progress
        ):
            raise ValueError("Completed history cannot be dropped")
        if previous and (running_children or set()) - {step.id for step in proposed.steps}:
            raise ValueError("Running delegate parents cannot be dropped")
        settings, _, _ = load_settings(self.root)
        scope = file_scope(self.root, proposed)
        progress = (
            adapt_todos(
                previous, call["args"], datetime.now(UTC), running_children=running_children
            )[1]
            if previous is not None and call["name"] == "write_todos"
            else [
                next(
                    (item for item in previous.progress if item.step_id == step.id),
                    StepProgress(step_id=step.id),
                )
                if previous
                else StepProgress(step_id=step.id)
                for step in proposed.steps
            ]
        )
        return PlanRecord(
            run_id=self.run_id,
            plan_id=previous.plan_id if previous else "plan-" + digest(self.run_id)[:24],
            revision=digest(review_material(self.root, proposed)),
            baseline_ids=(
                [step.id for step in proposed.steps]
                if reviewed or previous is None
                else previous.baseline_ids
            ),
            submission=proposed,
            progress=progress,
            adoption=(
                "approved"
                if reviewed
                else previous.adoption
                if previous and previous.submission == proposed
                else "automatic"
            ),
            file_scope=scope,
            settings=settings,
        )


def record_from_state(state: dict[str, Any]) -> PlanRecord | None:
    value = state.get("plan_record")
    return PlanRecord.model_validate(value) if value else None
