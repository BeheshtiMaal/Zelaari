"""Synthetic responses through real SDK HTTP clients and LangChain adapters."""

import json
from typing import Any

import anthropic
import httpx2
import pytest
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from pydantic import SecretStr


def sse(events: list[dict[str, Any]], named: bool = False) -> bytes:
    return "".join(
        (f"event: {event['type']}\n" if named else "") + "data: " + json.dumps(event) + "\n\n"
        for event in events
    ).encode()


@pytest.mark.parametrize("streaming", [False, True])
def test_generic_openai_drops_deepseek_reasoning(streaming: bool) -> None:
    def handle(request: httpx2.Request) -> httpx2.Response:
        assert request.url.host == "fixture.invalid"
        if streaming:
            return httpx2.Response(
                200,
                headers={"content-type": "text/event-stream"},
                content=sse(
                    [
                        {
                            "id": "fixture",
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {
                                        "role": "assistant",
                                        "reasoning_content": "PRIVATE_REASONING_FIXTURE",
                                    },
                                }
                            ],
                        },
                        {
                            "id": "fixture",
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {"content": "Answer"},
                                    "finish_reason": "stop",
                                }
                            ],
                        },
                    ]
                )
                + b"data: [DONE]\n\n",
            )
        return httpx2.Response(
            200,
            json={
                "id": "fixture",
                "model": "fixture",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "Answer",
                            "reasoning_content": "PRIVATE_REASONING_FIXTURE",
                        },
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    with httpx2.Client(transport=httpx2.MockTransport(handle)) as client:
        model = ChatOpenAI(
            model="fixture",
            api_key=SecretStr("synthetic-not-a-secret"),
            base_url="https://fixture.invalid/v1",
            http_client=client,
            use_responses_api=False,
            max_retries=0,
        )
        messages = list(model.stream("Hi")) if streaming else [model.invoke("Hi")]
    assert "Answer" in repr(messages)
    assert "PRIVATE_REASONING_FIXTURE" not in repr(messages)
    assert all(not any(b["type"] == "reasoning" for b in m.content_blocks) for m in messages)


@pytest.mark.parametrize("streaming", [False, True])
@pytest.mark.parametrize("thinking", [False, True])
def test_anthropic_thinking_transport(streaming: bool, thinking: bool) -> None:
    blocks: list[dict[str, Any]] = []
    if thinking:
        blocks.append({"type": "thinking", "thinking": "Provider thought", "signature": "fixture"})
    blocks.append({"type": "text", "text": "Answer"})
    message = {
        "id": "fixture",
        "type": "message",
        "role": "assistant",
        "model": "fixture",
        "content": blocks,
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {"input_tokens": 1, "output_tokens": 2},
    }

    def handle(request: httpx2.Request) -> httpx2.Response:
        assert request.url.host == "fixture.invalid"
        if not streaming:
            return httpx2.Response(200, json=message)
        events: list[dict[str, Any]] = [
            {"type": "message_start", "message": {**message, "content": [], "stop_reason": None}}
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
                        "delta": {"type": "thinking_delta", "thinking": "Provider thought"}
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
                    "usage": {"output_tokens": 2},
                },
                {"type": "message_stop"},
            ]
        )
        return httpx2.Response(
            200, headers={"content-type": "text/event-stream"}, content=sse(events, True)
        )

    with httpx2.Client(transport=httpx2.MockTransport(handle)) as client:
        sdk = anthropic.Anthropic(
            api_key="synthetic-not-a-secret",
            base_url="https://fixture.invalid",
            http_client=client,
            max_retries=0,
        )
        model = ChatAnthropic(
            model_name="fixture",
            api_key=SecretStr("synthetic-not-a-secret"),
            max_retries=0,
            timeout=10,
            stop=None,
        )
        model._client = sdk
        messages = list(model.stream("Hi")) if streaming else [model.invoke("Hi")]
    reasoning = [b for m in messages for b in m.content_blocks if b["type"] == "reasoning"]
    assert bool(reasoning) == thinking
    assert "Answer" in repr(messages)
    if thinking:
        assert "Provider thought" in repr(reasoning)
    assert "Answer" not in repr(reasoning)
