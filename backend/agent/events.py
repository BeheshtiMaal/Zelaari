"""Wire contract. Generate the renderer types from these Pydantic schemas."""

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter


class WireModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EventBase(WireModel):
    run_id: str
    seq: int = Field(ge=1)
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RunStarted(EventBase):
    type: Literal["run.started"] = "run.started"
    task: str
    model: str


class MessageDelta(EventBase):
    type: Literal["message.delta"] = "message.delta"
    message_id: str
    text: str


class ToolCall(EventBase):
    type: Literal["tool.call"] = "tool.call"
    call_id: str
    name: str
    args: dict[str, JsonValue]


class ToolResult(EventBase):
    type: Literal["tool.result"] = "tool.result"
    call_id: str
    text: str


class RunFinished(EventBase):
    type: Literal["run.finished"] = "run.finished"
    status: Literal["completed", "stopped", "error"]


class RunError(EventBase):
    type: Literal["run.error"] = "run.error"
    message: str


class FutureEvent(EventBase):
    """Reserved events: not emitted by the Phase 1 bridge."""

    type: Literal[
        "plan.created",
        "plan.step.updated",
        "reasoning.delta",
        "subagent.started",
        "subagent.finished",
        "context.summarized",
        "approval.requested",
        "approval.resolved",
        "question.asked",
        "question.answered",
        "ui.render",
        "test.result",
        "usage.updated",
    ]
    data: dict[str, JsonValue]


Event = Annotated[
    RunStarted | MessageDelta | ToolCall | ToolResult | RunFinished | RunError | FutureEvent,
    Field(discriminator="type"),
]
event_adapter: TypeAdapter[Event] = TypeAdapter(Event)


class RunRequest(WireModel):
    task: str = Field(min_length=1, max_length=32000)
    workspace: str
    model: Literal["demo", "openai-compatible"] = "demo"


class RunResponse(WireModel):
    run_id: str


class HealthResponse(WireModel):
    status: Literal["ok"] = "ok"


class Protocol(WireModel):
    """Schema-generation envelope only; never sent over the wire."""

    event: Event
    run_request: RunRequest
    run_response: RunResponse
    health: HealthResponse
