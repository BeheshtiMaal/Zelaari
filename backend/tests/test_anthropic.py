import asyncio
import json
from typing import Any

import anthropic
import httpx2
import pytest
from langchain_anthropic import ChatAnthropic
from pydantic import SecretStr

from agent.meter import content_parts
from providers.base import ModelInput
from providers.probe import test_connection as probe
from store.catalog import Catalog, Credential


@pytest.mark.parametrize("thinking", [False, True])
def test_native_anthropic_http_probe_and_thinking_stream(thinking: bool) -> None:
    async def scenario() -> None:
        catalog = Catalog()
        catalog.credential(Credential(id="native", key=SecretStr("synthetic-native-key")))
        catalog.save(
            ModelInput(
                id="native", name="Native", model="fixture", base_url="https://api.anthropic.com"
            )
        )
        requests: list[dict[str, Any]] = []
        blocks: list[dict[str, Any]] = []
        if thinking:
            blocks.append(
                {"type": "thinking", "thinking": "Actual thought", "signature": "fixture"}
            )
        blocks.append({"type": "text", "text": "Answer"})

        async def handle(request: httpx2.Request) -> httpx2.Response:
            data = json.loads(request.content)
            requests.append(data)
            message = {
                "id": "native-fixture",
                "type": "message",
                "role": "assistant",
                "model": "fixture",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "probe",
                        "name": "harness_probe",
                        "input": {"marker": "connection-ok"},
                    }
                ],
                "stop_reason": "tool_use",
                "stop_sequence": None,
                "usage": {"input_tokens": 10, "output_tokens": 5},
            }
            if not data.get("stream"):
                return httpx2.Response(200, json=message)
            events: list[dict[str, Any]] = [
                {
                    "type": "message_start",
                    "message": {**message, "content": [], "stop_reason": None},
                }
            ]
            for index, block in enumerate(blocks):
                is_thinking = block["type"] == "thinking"
                events.extend(
                    [
                        {
                            "type": "content_block_start",
                            "index": index,
                            "content_block": {"type": "thinking", "thinking": "", "signature": ""}
                            if is_thinking
                            else {"type": "text", "text": ""},
                        },
                        {
                            "type": "content_block_delta",
                            "index": index,
                            "delta": {"type": "thinking_delta", "thinking": "Actual thought"}
                            if is_thinking
                            else {"type": "text_delta", "text": "Answer"},
                        },
                        {"type": "content_block_stop", "index": index},
                    ]
                )
            events.extend(
                [
                    {
                        "type": "message_delta",
                        "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                        "usage": {"output_tokens": 5},
                    },
                    {"type": "message_stop"},
                ]
            )
            return httpx2.Response(
                200,
                headers={"content-type": "text/event-stream"},
                content="".join(
                    f"event: {event['type']}\ndata: {json.dumps(event)}\n\n" for event in events
                ).encode(),
            )

        async def metadata(*args: Any) -> object:
            return None

        async with httpx2.AsyncClient(transport=httpx2.MockTransport(handle)) as client:
            sdk = anthropic.AsyncAnthropic(
                api_key="synthetic-native-key", http_client=client, max_retries=0
            )
            model = ChatAnthropic(
                model_name="fixture",
                api_key=SecretStr("synthetic-native-key"),
                max_retries=0,
                timeout=10,
                stop=None,
            )
            model._async_client = sdk
            result = await probe(catalog, "native", factory=lambda *args: model, metadata=metadata)
            assert result.supports_tools
            assert requests[0]["tools"][0]["name"] == "harness_probe"
            chunks = [chunk async for chunk in model.astream("Hello")]
            assert "".join(content_parts(chunk)[0] for chunk in chunks) == "Answer"
            assert "".join(content_parts(chunk)[1] for chunk in chunks) == (
                "Actual thought" if thinking else ""
            )

    asyncio.run(scenario())
