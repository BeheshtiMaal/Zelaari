"""Offline model exercising real agent tool dispatch, not a simulated run."""

import asyncio
import json
import re
from collections.abc import AsyncIterator, Callable, Iterator, Sequence
from typing import Any

from langchain_core.callbacks import AsyncCallbackManagerForLLMRun, CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool


class DemoModel(BaseChatModel):
    delay: float = 0.012

    @property
    def _llm_type(self) -> str:
        return "codeharness-offline-demo"

    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | Callable[..., Any] | BaseTool],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> Runnable[Any, Any]:
        return self

    def answer(self, messages: list[BaseMessage]) -> AIMessage:
        results = [message for message in messages if isinstance(message, ToolMessage)]
        if not results:
            task = str(messages[-1].content)
            match = re.search(r"[\w./\\-]+\.(?:md|txt|py|json|ts|tsx)\b", task)
            path = match.group(0) if match else "README.md"
            return AIMessage(
                content="در حال خواندن فایل…",
                tool_calls=[
                    {
                        "name": "read_file",
                        "args": {"file_path": path},
                        "id": "demo-read",
                        "type": "tool_call",
                    }
                ],
            )
        text = str(results[-1].content)
        # A deterministic excerpt of the real tool result; no invented file facts.
        excerpt = "\n".join(text.splitlines()[:8])[:650]
        return AIMessage(
            content=(
                'root = Stack([Callout("خواندن فایل پایان یافت"), '
                f'KeyValue("خلاصهٔ فایل", {json.dumps(excerpt, ensure_ascii=False)})]);'
            )
        )

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=self.answer(messages))])

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        message = self.answer(messages)
        text = str(message.content)
        for offset in range(0, len(text), 16):
            yield ChatGenerationChunk(message=AIMessageChunk(content=text[offset : offset + 16]))
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

    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        for chunk in self._stream(messages, stop):
            await asyncio.sleep(self.delay)
            yield chunk
