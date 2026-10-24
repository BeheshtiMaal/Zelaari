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

SUMMARY_LIMIT = 8000


def summary_path(root: Path, run_id: str) -> Path:
    return storage_path(root, f"context/summaries/{run_id}.md")


def summary_text(change: dict[str, Any]) -> str | None:
    """The summary the middleware just produced, or `None` for other updates."""
    event = change.get("_summarization_event")
    if not isinstance(event, dict):
        return None
    message = event.get("summary_message")
    content = message.get("content") if isinstance(message, dict) else None
    text = content if isinstance(content, str) else getattr(message, "content", None)
    return text if isinstance(text, str) and text.strip() else None


def save_summary(root: Path, run_id: str, change: dict[str, Any], offload: bool) -> None:
    """Persist the redacted summary so a new chat can start from it.

    Offload off means the evicted history is not kept, so there is nothing to hand on.
    """
    if not offload:
        return
    text = summary_text(change)
    if text is None:
        return
    from tools.atomic import atomic_write

    atomic_write(summary_path(root, run_id), text[:SUMMARY_LIMIT])


def read_summary(root: Path, run_id: str) -> tuple[str, float] | None:
    path = summary_path(root, run_id)
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")[:SUMMARY_LIMIT]
    return (text, path.stat().st_mtime) if text.strip() else None


def seed_block(summary: str) -> str:
    """The bounded block a new run starts with instead of replaying the old one."""
    body = summary.strip()[:SUMMARY_LIMIT]
    return f"Previous conversation summary\n\n{body}"


def summary_backend(
    root: Path, redactor: Redactor, cancelled: Event | None = None, *, offload: bool = True
) -> CompositeBackend:
    """Only the summarizer receives this private artifact-storage route."""
    routes: dict[str, BackendProtocol] = {}
    if offload:
        # With offload off there is no artifact route, so evicted history is not
        # recoverable: the setting is honoured instead of quietly ignored.
        routes["/.harness/context/"] = WorkspaceBackend(
            storage_path(root, "context"), redactor, cancelled=cancelled
        )
    return CompositeBackend(
        default=ReadOnlyWorkspaceBackend(root, redactor),
        routes=routes,
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
