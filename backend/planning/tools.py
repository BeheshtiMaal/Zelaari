"""Model-visible plan submission; the pre-tool permission barrier owns acceptance."""

from langchain_core.tools import BaseTool, StructuredTool

from planning.types import PlanSubmission


def build_submit_plan() -> BaseTool:
    def submit_plan(**kwargs: object) -> str:
        return (
            "Plan accepted. Use write_todos with '[step_id] title'; start one step before effects."
        )

    return StructuredTool.from_function(
        submit_plan,
        name="submit_plan",
        description=(
            "Submit small ordered steps with stable IDs and expected workspace-relative file globs "
            "before mutations or commands. Report deviations by submitting a revised plan. "
            "verify_command is descriptive and is never executed by this tool."
        ),
        args_schema=PlanSubmission,
    )
