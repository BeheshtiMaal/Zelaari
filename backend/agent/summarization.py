"""Keep the installed compaction policy while scrubbing its separate model path."""

import hashlib
import math
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from pathlib import Path
from threading import Event
from typing import Annotated, Any, NotRequired

from deepagents.backends import CompositeBackend
from deepagents.backends.protocol import BackendProtocol
from deepagents.middleware.summarization import (
    SummarizationMiddleware,
    SummarizationState,
    compute_summarization_defaults,
)
from langchain.agents.middleware.types import (
    ExtendedModelResponse,
    ModelRequest,
    ModelResponse,
    OmitFromInput,
)
from langchain_core.callbacks import get_usage_metadata_callback
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage

from planning.readonly import ReadOnlyWorkspaceBackend
from store.secrets import Redactor
from tools.fs import WorkspaceBackend
from tools.jail import storage_path

summary_usage: ContextVar[dict[str, Any] | None] = ContextVar("summary_usage", default=None)


def summary_backend(
    root: Path, redactor: Redactor, cancelled: Event | None = None
) -> CompositeBackend:
    """Only the summarizer receives this private artifact-storage route."""
    return CompositeBackend(
        default=ReadOnlyWorkspaceBackend(root, redactor),
        routes={
            "/.harness/context/": WorkspaceBackend(
                storage_path(root, "context"),
                redactor,
                cancelled=cancelled,
            )
        },
        artifacts_root="/.harness/context",
    )


class SummaryState(SummarizationState):
    summary_notice: NotRequired[Annotated[dict[str, Any], OmitFromInput]]


class RedactingSummarization(SummarizationMiddleware):
    state_schema = SummaryState

    @property
    def name(self) -> str:
        # Replace the factory's summarizer by its installed middleware slot name.
        return "SummarizationMiddleware"

    def __init__(
        self, model: BaseChatModel, backend: BackendProtocol, redactor: Redactor, **settings: Any
    ) -> None:
        self.redactor = redactor
        defaults = compute_summarization_defaults(model)
        super().__init__(
            model,
            backend=backend,
            **{**defaults, "trim_tokens_to_summarize": None, **settings},
        )

    def clean(self, messages: list[AnyMessage]) -> list[AnyMessage]:
        return [
            type(message).model_validate(self.redactor.value(message.model_dump(mode="json")))
            for message in messages
        ]

    async def _acreate_summary(self, messages_to_summarize: list[AnyMessage]) -> str:
        clean = self.clean(messages_to_summarize)
        with get_usage_metadata_callback() as usage:
            summary = await super()._acreate_summary(clean)
        self.remember_usage(clean, summary, usage.usage_metadata)
        return self.redactor.text(summary)

    def _create_summary(self, messages_to_summarize: list[AnyMessage]) -> str:
        clean = self.clean(messages_to_summarize)
        with get_usage_metadata_callback() as usage:
            summary = super()._create_summary(clean)
        self.remember_usage(clean, summary, usage.usage_metadata)
        return self.redactor.text(summary)

    def remember_usage(self, messages: list[AnyMessage], summary: str, usage: Any) -> None:
        if usage:
            summary_usage.set(
                {
                    "input_tokens": sum(value["input_tokens"] for value in usage.values()),
                    "output_tokens": sum(value["output_tokens"] for value in usage.values()),
                    "estimated": False,
                }
            )
        else:
            prompt = self._lc_helper._format_summary_prompt(messages)
            summary_usage.set(
                {
                    "input_tokens": max(1, math.ceil(len(prompt) / 4)),
                    "output_tokens": max(1, math.ceil(len(summary) / 4)),
                    "estimated": True,
                }
            )

    @staticmethod
    def attach_usage(
        response: ModelResponse | ExtendedModelResponse, request: ModelRequest
    ) -> None:
        usage = summary_usage.get()
        if isinstance(response, ExtendedModelResponse) and response.command:
            update = response.command.update
            if isinstance(update, dict) and isinstance(update.get("_summarization_event"), dict):
                update["_summarization_event"]["summary_message"].additional_kwargs[
                    "_harness_usage"
                ] = usage
                event = update["_summarization_event"]
                scope = request.state.get("child_activity_scope") or request.state.get(
                    "activity_scope"
                )
                prior = request.state.get("_summarization_event")
                previous = prior if isinstance(prior, dict) else {}
                count = event["cutoff_index"] - previous.get("cutoff_index", 0)
                update["summary_notice"] = {
                    "operation_id": hashlib.sha256((str(scope) + str(event)).encode()).hexdigest(),
                    "affected_messages": count if count > 0 else None,
                    "usage": usage,
                    "scope": scope,
                }

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse | ExtendedModelResponse:
        token = summary_usage.set(None)
        try:
            response = await super().awrap_model_call(request, handler)
            self.attach_usage(response, request)
            return response
        finally:
            summary_usage.reset(token)

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse | ExtendedModelResponse:
        token = summary_usage.set(None)
        try:
            response = super().wrap_model_call(request, handler)
            self.attach_usage(response, request)
            return response
        finally:
            summary_usage.reset(token)

    async def _aoffload_to_backend(
        self, backend: BackendProtocol, messages: list[AnyMessage], session_id: str
    ) -> str | None:
        return await super()._aoffload_to_backend(backend, self.clean(messages), session_id)

    def _offload_to_backend(
        self, backend: BackendProtocol, messages: list[AnyMessage], session_id: str
    ) -> str | None:
        return super()._offload_to_backend(backend, self.clean(messages), session_id)
