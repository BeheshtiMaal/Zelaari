"""Question tools execute only after the middleware has obtained a human answer."""

from langchain_core.tools import StructuredTool

from questions.types import Question, QuestionInput


def build_ask_question() -> StructuredTool:
    def unanswered(questions: list[Question]) -> str:
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
