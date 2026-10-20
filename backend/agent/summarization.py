"""Keep the installed compaction policy while scrubbing its separate model path."""

from typing import Any

from deepagents.backends.protocol import BackendProtocol
from deepagents.middleware.summarization import (
    SummarizationMiddleware,
    compute_summarization_defaults,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage

from store.secrets import Redactor


class RedactingSummarization(SummarizationMiddleware):
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
        summary = await super()._acreate_summary(self.clean(messages_to_summarize))
        return self.redactor.text(summary)

    def _create_summary(self, messages_to_summarize: list[AnyMessage]) -> str:
        summary = super()._create_summary(self.clean(messages_to_summarize))
        return self.redactor.text(summary)

    async def _aoffload_to_backend(
        self, backend: BackendProtocol, messages: list[AnyMessage], session_id: str
    ) -> str | None:
        return await super()._aoffload_to_backend(backend, self.clean(messages), session_id)

    def _offload_to_backend(
        self, backend: BackendProtocol, messages: list[AnyMessage], session_id: str
    ) -> str | None:
        return super()._offload_to_backend(backend, self.clean(messages), session_id)
