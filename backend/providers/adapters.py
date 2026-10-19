"""Provider-aware adapters. Private overrides verified against pinned 1.7.2."""

from typing import Any

import openai
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGenerationChunk, ChatResult
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from providers.base import ProviderRecord


class ReasoningOpenAI(ChatOpenAI):
    def _convert_chunk_to_generation_chunk(
        self,
        chunk: dict[str, Any],
        default_chunk_class: type,
        base_generation_info: dict[str, Any] | None,
    ) -> ChatGenerationChunk | None:
        result = super()._convert_chunk_to_generation_chunk(
            chunk, default_chunk_class, base_generation_info
        )
        choices = chunk.get("choices", [])
        delta = choices[0].get("delta") if choices else None
        if result and isinstance(delta, dict) and isinstance(delta.get("reasoning_content"), str):
            result.message.additional_kwargs["reasoning_content"] = delta["reasoning_content"]
        return result

    def _create_chat_result(
        self,
        response: dict[str, Any] | openai.BaseModel,
        generation_info: dict[str, Any] | None = None,
    ) -> ChatResult:
        result = super()._create_chat_result(response, generation_info)
        data = response if isinstance(response, dict) else response.model_dump()
        for generation, choice in zip(result.generations, data.get("choices", []), strict=False):
            reasoning = choice.get("message", {}).get("reasoning_content")
            if isinstance(reasoning, str):
                generation.message.additional_kwargs["reasoning_content"] = reasoning
        return result

    def _get_request_payload(
        self,
        input_: LanguageModelInput,
        *,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        result = super()._get_request_payload(input_, stop=stop, **kwargs)
        for message, outgoing in zip(
            self._convert_input(input_).to_messages(), result.get("messages", []), strict=False
        ):
            if isinstance(message, AIMessage) and "reasoning_content" in message.additional_kwargs:
                outgoing["reasoning_content"] = message.additional_kwargs["reasoning_content"]
        return result


def chat_model(record: ProviderRecord, key: SecretStr) -> BaseChatModel:
    if record.kind == "anthropic":
        return ChatAnthropic(
            model_name=record.model,
            api_key=key,
            base_url=record.base_url,
            max_retries=0,
            timeout=30,
            max_tokens_to_sample=4096,
        )
    return ReasoningOpenAI(
        model=record.model,
        base_url=record.base_url,
        api_key=key,
        use_responses_api=False,
        streaming=True,
        stream_usage=True,
        max_retries=0,
        timeout=30,
    )
