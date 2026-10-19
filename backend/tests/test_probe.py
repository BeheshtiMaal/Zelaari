import asyncio
import json
from typing import Any

import httpx
import pytest
from langchain_core.messages import AIMessageChunk
from pydantic import SecretStr

from providers.adapters import ReasoningOpenAI
from providers.base import ModelInput
from providers.context import detect_context
from providers.probe import test_connection as probe
from store.catalog import Catalog, Credential


def test_context_precedence_and_validation() -> None:
    assert (
        detect_context("native", {"data": [{"id": "native", "max_input_tokens": 200000}]}).tokens
        == 200000
    )
    assert (
        detect_context("gpt-4.1", {"data": [{"id": "gpt-4.1", "context_window": 98765}]}).tokens
        == 98765
    )
    assert detect_context("gpt-4.1", error="maximum context length is 123 tokens").source == "table"
    assert (
        detect_context("unknown", error="maximum context length is 65,536 tokens").tokens == 65536
    )
    for metadata in [
        None,
        {"data": [{"id": "wrong", "context_length": 123}]},
        {"data": [{"id": "unknown", "context_window": -1}]},
    ]:
        assert detect_context("unknown", metadata).estimated
        assert detect_context("unknown", metadata).tokens == 32768


def test_cancelling_metadata_probe_restores_untested_state() -> None:
    async def scenario() -> None:
        catalog = Catalog()
        catalog.credential(Credential(id="mine", key=SecretStr("original-key")))
        catalog.save(ModelInput(id="mine", name="Mine", model="unknown", base_url="https://x/v1"))
        started = asyncio.Event()

        async def metadata(*args: Any) -> object:
            started.set()
            await asyncio.Event().wait()
            return None

        task = asyncio.create_task(probe(catalog, "mine", metadata=metadata))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert catalog.data.models["mine"].probe.status == "untested"
        assert not catalog.data.models["mine"].supports_tools

    asyncio.run(scenario())


def test_key_rotation_during_probe_cannot_authorize_old_configuration() -> None:
    async def scenario() -> None:
        catalog = Catalog()
        catalog.credential(Credential(id="mine", key=SecretStr("original-key")))
        catalog.save(ModelInput(id="mine", name="Mine", model="unknown", base_url="https://x/v1"))
        started = asyncio.Event()
        release = asyncio.Event()

        async def metadata(*args: Any) -> object:
            return None

        async def handle(request: httpx.Request) -> httpx.Response:
            started.set()
            await release.wait()
            return httpx.Response(
                200,
                json={
                    "id": "probe",
                    "model": "unknown",
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": "tool_calls",
                            "message": {
                                "role": "assistant",
                                "content": "",
                                "tool_calls": [
                                    {
                                        "id": "p",
                                        "type": "function",
                                        "function": {
                                            "name": "harness_probe",
                                            "arguments": '{"marker":"connection-ok"}',
                                        },
                                    }
                                ],
                            },
                        }
                    ],
                },
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            model = ReasoningOpenAI(
                model="unknown",
                api_key=SecretStr("original-key"),
                base_url="https://x/v1",
                http_async_client=client,
                max_retries=0,
                use_responses_api=False,
            )
            task = asyncio.create_task(
                probe(catalog, "mine", factory=lambda *args: model, metadata=metadata)
            )
            await started.wait()
            catalog.credential(Credential(id="mine", key=SecretStr("replacement-key")))
            release.set()
            result = await task
            assert not result.supports_tools and result.probe.status == "untested"
            with pytest.raises(ValueError):
                catalog.require("mine")

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "statuses,expected,attempts",
    [
        ([200], None, 1),
        ([401], "unauthorized", 1),
        ([429, 429, 429], "rate_limit", 3),
        ([429, 200], None, 2),
        ([201], "no_tools", 1),
        ([202], "no_tools", 1),
    ],
)
def test_actual_compatible_probe_transport(
    statuses: list[int], expected: str | None, attempts: int
) -> None:
    async def scenario() -> None:
        requests: list[dict[str, Any]] = []
        waits: list[float] = []
        catalog = Catalog()
        catalog.credential(Credential(id="mine", key=SecretStr("synthetic-canary")))
        catalog.save(ModelInput(id="mine", name="Mine", model="unknown", base_url="https://x/v1"))

        async def handle(request: httpx.Request) -> httpx.Response:
            requests.append(json.loads(request.content))
            status = statuses[min(len(requests) - 1, len(statuses) - 1)]
            if status in {401, 429}:
                return httpx.Response(status, json={"error": {"message": "synthetic-canary"}})
            message: dict[str, Any] = {"role": "assistant", "content": ""}
            if status != 201:
                message["tool_calls"] = [
                    {
                        "id": "p",
                        "type": "function",
                        "function": {
                            "name": "harness_probe",
                            "arguments": json.dumps(
                                {"marker": "connection-ok" if status == 200 else "wrong"}
                            ),
                        },
                    }
                ]
            return httpx.Response(
                200,
                json={
                    "id": "probe",
                    "model": "unknown",
                    "choices": [{"index": 0, "finish_reason": "tool_calls", "message": message}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14},
                },
            )

        async def metadata(*args: Any) -> object:
            return None

        async def sleep(seconds: float) -> None:
            assert catalog.data.models["mine"].probe.status == "retrying"
            assert catalog.data.models["mine"].probe.retry_seconds == seconds
            waits.append(seconds)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:

            def factory(*args: Any) -> ReasoningOpenAI:
                return ReasoningOpenAI(
                    model="unknown",
                    api_key=SecretStr("synthetic-canary"),
                    base_url="https://x/v1",
                    http_async_client=client,
                    max_retries=0,
                    use_responses_api=False,
                )

            result = await probe(catalog, "mine", factory=factory, metadata=metadata, sleep=sleep)
        assert result.probe.code == expected
        assert len(requests) == attempts
        assert waits == [2.0, 4.0][: attempts - 1]
        assert all(
            request["tools"][0]["function"]["name"] == "harness_probe" for request in requests
        )
        assert "synthetic-canary" not in result.model_dump_json()

    asyncio.run(scenario())


def test_compatible_reasoning_conversion_and_tool_roundtrip() -> None:
    model = ReasoningOpenAI(model="fixture", api_key=SecretStr("fixture"))
    chunk = model._convert_chunk_to_generation_chunk(
        {"choices": [{"delta": {"content": "answer", "reasoning_content": "actual reasoning"}}]},
        AIMessageChunk,
        None,
    )
    assert chunk and chunk.message.content == "answer"
    assert chunk.message.additional_kwargs["reasoning_content"] == "actual reasoning"
    result = model._create_chat_result(
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "answer",
                        "reasoning_content": "reason",
                    },
                    "finish_reason": "stop",
                }
            ]
        }
    )
    outgoing = model._get_request_payload([result.generations[0].message])
    assert outgoing["messages"][0]["reasoning_content"] == "reason"
