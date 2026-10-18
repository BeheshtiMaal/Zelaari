"""Deterministic, tool-bindable offline chat model for real agent invocations."""

import json
from collections.abc import Callable, Iterator, Sequence
from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from pydantic import Field, PrivateAttr


class DemoModel(BaseChatModel):
    script: list[AIMessage]
    requests: list[list[BaseMessage]] = Field(default_factory=list)
    bound_names: list[str] = Field(default_factory=list)
    _cursor: int = PrivateAttr(default=0)

    @property
    def _llm_type(self) -> str:
        return "offline-scripted-spike"

    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | Callable[..., Any] | BaseTool],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> Runnable[Any, Any]:
        self.bound_names = [
            t.name
            if isinstance(t, BaseTool)
            else str(t.get("name", ""))
            if isinstance(t, dict)
            else getattr(t, "__name__", "")
            for t in tools
        ]
        return self

    def next_message(self, messages: list[BaseMessage]) -> AIMessage:
        self.requests.append(messages)
        if self._cursor >= len(self.script):
            raise RuntimeError("Demo script exhausted")
        message = self.script[self._cursor]
        self._cursor += 1
        return message

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=self.next_message(messages))])

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        message = self.next_message(messages)
        assert isinstance(message.content, str)
        for text in message.content.split(" "):
            if text:
                yield ChatGenerationChunk(message=AIMessageChunk(content=text + " "))
        for index, call in enumerate(message.tool_calls):
            yield ChatGenerationChunk(
                message=AIMessageChunk(
                    content="",
                    tool_call_chunks=[
                        {
                            "name": call["name"],
                            "args": json.dumps(call["args"]),
                            "id": call["id"],
                            "index": index,
                            "type": "tool_call_chunk",
                        }
                    ],
                )
            )


def call(name: str, args: dict[str, Any], identifier: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": name,
                "args": args,
                "id": identifier,
                "type": "tool_call",
            }
        ],
    )
