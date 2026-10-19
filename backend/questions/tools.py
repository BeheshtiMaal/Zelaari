"""Question tools execute only after the middleware has obtained a human answer."""

from langchain_core.tools import StructuredTool

from questions.types import FailureContext, InterviewSummary, Question, QuestionInput


def build_ask_question() -> StructuredTool:
    def unanswered(
        questions: list[Question],
        presentation: str = "standard",
        context: str = "",
        failure: FailureContext | None = None,
    ) -> str:
        return "Question could not be answered: the human barrier was unavailable."

    return StructuredTool.from_function(
        unanswered,
        name="ask_user_question",
        args_schema=QuestionInput,
        description=(
            "Ask 1 to 3 structured questions only when the answer cannot be found "
            "by reading the project. Read relevant project context first. Use short "
            "headers, stable IDs, 2 to 4 options with descriptions, and single/multi/rank "
            "types. Other text is always supplied by the UI. Declined is not consent."
        ),
    )


def build_finish_interview() -> StructuredTool:
    def finish(objective: str, scope: str, constraints: str, acceptance: str) -> str:
        return InterviewSummary(
            objective=objective, scope=scope, constraints=constraints, acceptance=acceptance
        ).model_dump_json()

    return StructuredTool.from_function(
        finish,
        name="finish_interview",
        args_schema=InterviewSummary,
        description=(
            "In /grill mode, after answered interview batches specify the task, persist "
            "this structured readiness summary. Only a subsequent turn may begin "
            "implementation. Never call after decline."
        ),
    )
