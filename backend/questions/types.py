"""Identity-bound question and mixed human-barrier contracts."""

from datetime import UTC, datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from permissions.types import ApprovalAnswer, ApprovalRequest

Identifier = Annotated[str, StringConstraints(pattern=r"^[a-zA-Z0-9_-]{1,128}$")]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
QuestionText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
]


class QuestionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QuestionOption(QuestionModel):
    id: Identifier
    label: ShortText
    description: QuestionText


class Question(QuestionModel):
    id: Identifier
    header: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
    text: QuestionText
    type: Literal["single", "multi", "rank"] = "single"
    options: list[QuestionOption] = Field(min_length=2, max_length=4)

    @model_validator(mode="after")
    def distinct_options(self) -> Self:
        if len({option.id for option in self.options}) != len(self.options):
            raise ValueError("Duplicate option IDs")
        return self


class QuestionInput(QuestionModel):
    questions: list[Question] = Field(min_length=1, max_length=3)
    presentation: Literal["standard", "exhausted"] = "standard"
    context: str = Field(default="", max_length=12000)

    @model_validator(mode="after")
    def distinct_questions(self) -> Self:
        if len({question.id for question in self.questions}) != len(self.questions):
            raise ValueError("Duplicate question IDs")
        return self


class QuestionRequest(QuestionInput):
    kind: Literal["question"] = "question"
    run_id: str
    call_id: str = Field(min_length=1, max_length=256)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class QuestionSelection(QuestionModel):
    question_id: Identifier
    option_ids: list[Identifier] = Field(default_factory=list, max_length=4)
    other: str | None = Field(default=None, min_length=1, max_length=4000)
    hint: str | None = Field(default=None, min_length=1, max_length=4000)


class QuestionDecision(QuestionModel):
    kind: Literal["question"] = "question"
    interrupt_id: str = Field(min_length=1, max_length=256)
    status: Literal["answered", "declined"]
    answers: list[QuestionSelection] = Field(default_factory=list, max_length=3)


class QuestionAnswer(QuestionDecision):
    run_id: str
    call_id: str

    def validate_request(self, request: QuestionRequest) -> None:
        if self.run_id != request.run_id or self.call_id != request.call_id:
            raise ValueError("Question identity mismatch")
        if self.status == "declined":
            if self.answers:
                raise ValueError("Declined questions cannot have selections")
            return
        if len(self.answers) != len(request.questions) or {
            answer.question_id for answer in self.answers
        } != {question.id for question in request.questions}:
            raise ValueError("Answer every question exactly once")
        for question in request.questions:
            answer = next(item for item in self.answers if item.question_id == question.id)
            ids = set(answer.option_ids)
            offered = {option.id for option in question.options}
            if answer.hint is not None and (request.presentation != "exhausted" or ids != {"retry"}
                                            or not answer.hint.strip()):
                raise ValueError("Hint belongs to exhausted retry")
            if len(ids) != len(answer.option_ids) or not ids <= offered:
                raise ValueError("Invalid option identity")
            other = bool(answer.other and answer.other.strip())
            if answer.other is not None and not other:
                raise ValueError("Other cannot be blank")
            if question.type == "single" and len(ids) + int(other) != 1:
                raise ValueError("Choose one option or Other")
            if question.type == "multi" and not (ids or other):
                raise ValueError("Choose an option or Other")
            if question.type == "rank" and ids != offered:
                raise ValueError("Rank every option exactly once")


class QuestionRecord(QuestionModel):
    request: QuestionRequest
    interrupt_id: str
    status: Literal["pending", "answered", "declined", "cancelled"] = "pending"
    answer: QuestionAnswer | None = None
    resolved_at: datetime | None = None


class HumanBatch(QuestionModel):
    kind: Literal["human"] = "human"
    approvals: list[ApprovalRequest] = Field(default_factory=list)
    questions: list[QuestionRequest] = Field(default_factory=list)


class HumanBatchAnswer(QuestionModel):
    kind: Literal["human"] = "human"
    approvals: dict[str, ApprovalAnswer] = Field(default_factory=dict)
    questions: dict[str, QuestionAnswer] = Field(default_factory=dict)


class InterviewSummary(QuestionModel):
    objective: QuestionText
    scope: QuestionText
    constraints: QuestionText
    acceptance: QuestionText
