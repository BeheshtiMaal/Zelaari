"""What is actually filling the window, measured with the summarizer's own counter.

The ring, the popover and the compaction trigger all read the same
`count_tokens_approximately` call, so the marker on the bar and the moment the
summarizer fires cannot disagree.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import AgentState
from langchain_core.messages import SystemMessage, ToolMessage
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.runtime import Runtime
from pydantic import BaseModel, ConfigDict, Field


class ContextBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: int = Field(ge=0)
    tool_results: int = Field(ge=0)
    system: int = Field(ge=0)
    skills: int = Field(ge=0)
    memory: int = Field(ge=0)
    estimated: bool = True


def breakdown(
    messages: Sequence[Any],
    system: str = "",
    tools: Sequence[Any] = (),
    skills: str = "",
    memory: str = "",
) -> ContextBreakdown:
    """Split the prompt into the rows the popover shows.

    Skills and memory are part of the system text the model receives, so their rows are
    measured from their own blocks and *subtracted* from the system row: the five rows
    still add up to the same total.
    """
    results = [message for message in messages if isinstance(message, ToolMessage)]
    prompt = [message for message in messages if isinstance(message, SystemMessage)]
    plain = [
        message
        for message in messages
        if not isinstance(message, (ToolMessage, SystemMessage))
    ]
    text = "\n".join([*(str(message.content) for message in prompt), system]).strip()
    total = count_tokens_approximately(
        [SystemMessage(content=text)] if text else [], tools=list(tools) or None
    )
    skill_tokens = _tokens(skills)
    memory_tokens = _tokens(memory)
    return ContextBreakdown(
        messages=count_tokens_approximately(plain),
        tool_results=count_tokens_approximately(results),
        system=max(0, total - skill_tokens - memory_tokens),
        skills=skill_tokens,
        memory=memory_tokens,
        estimated=True,
    )


def _tokens(text: str) -> int:
    return (
        count_tokens_approximately([SystemMessage(content=text)]) if text.strip() else 0
    )


@dataclass
class Window:
    """The prompt the model last received, so the breakdown describes a real call."""

    system: str = ""
    tools: list[Any] = field(default_factory=list)
    messages: list[Any] = field(default_factory=list)
    skills: str = ""
    memory: str = ""

    def breakdown(self) -> ContextBreakdown:
        return breakdown(self.messages, self.system, self.tools, self.skills, self.memory)


class ContextMiddleware(AgentMiddleware[AgentState[Any], Any, Any]):
    """Remembers the prompt before each model call; it changes no state of its own."""

    def __init__(self, window: Window) -> None:
        self.window = window

    async def abefore_model(
        self, state: AgentState[Any], runtime: Runtime[Any]
    ) -> dict[str, Any] | None:
        self.window.messages = list(state.get("messages", []))
        return None
