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

from providers.question_demo import demo_question


class DemoModel(BaseChatModel):
    delay: float = 0.012
    locale: str = "fa"

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
        task = next((str(message.content) for message in messages if message.type == "human"), "")
        question_reply = demo_question(task, results, self.locale)
        if question_reply is not None:
            return question_reply
        edit = re.fullmatch(r"demo edit ([\w./\\-]+): (.+?) => (.+)", task, re.DOTALL)
        if edit and results and results[-1].name == "read_file":
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "edit_file",
                        "args": {
                            "file_path": edit[1],
                            "old_string": edit[2],
                            "new_string": edit[3],
                        },
                        "id": "demo-edit",
                        "type": "tool_call",
                    }
                ],
            )
        if not results:
            match = re.search(r"[\w./\\-]+\.(?:md|txt|py|json|ts|tsx)\b", task)
            path = edit[1] if edit else match.group(0) if match else "README.md"
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
