"""A side-effect-free tool call and a bounded retry budget."""

import asyncio
from collections.abc import Awaitable, Callable

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage

from providers.adapters import chat_model
from providers.base import Probe, ProviderRecord
from providers.context import detect_context, model_metadata
from store.catalog import Catalog

PROBE_TOOL = {
    "type": "function", "function": {
        "name": "harness_probe", "description": "Return the supplied connection-test marker.",
        "parameters": {"type": "object", "properties": {"marker": {"type": "string"}},
                       "required": ["marker"], "additionalProperties": False},
    },
}


async def test_connection(
    catalog: Catalog, identifier: str, *,
    factory: Callable[..., BaseChatModel] = chat_model,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    metadata: Callable[..., Awaitable[object]] = model_metadata,
) -> ProviderRecord:
    if identifier == "demo":
        return catalog.require("demo")
    record = catalog.data.models.get(identifier)
    if not record or identifier not in catalog.keys:
        raise ValueError("Unknown model or missing key")
    if record.probe.status in {"testing", "retrying"}:
        raise ValueError("Test already running")
    record.supports_tools = False
    key = catalog.keys[identifier]
    record.probe = Probe(status="testing")
    catalog.persist()
    context_metadata = await metadata(record, key)
    record.context = detect_context(record.model, context_metadata)
    try:
        model = factory(record.model_copy(deep=True), key)
        bound = model.bind_tools([PROBE_TOOL])
        for attempt in range(1, 4):
            record.probe = Probe(status="testing", attempt=attempt)
            try:
                answer = await bound.ainvoke([HumanMessage(
                    content="Call harness_probe exactly once with marker 'connection-ok'."
                )])
                valid = isinstance(answer, AIMessage) and len(answer.tool_calls) == 1
                if valid:
                    call = answer.tool_calls[0]
                    valid = call["name"] == "harness_probe" and call["args"] == {
                        "marker": "connection-ok"
                    }
                record.supports_tools = valid
                record.probe = Probe(
                    status="ok" if valid else "error", code=None if valid else "no_tools",
                    attempt=attempt,
                )
                break
            except Exception as error:
                status = getattr(error, "status_code", None)
                parsed = detect_context(record.model, context_metadata, str(error))
                record.context = parsed
                if status == 429 and attempt < 3:
                    seconds = float(2 ** attempt)
                    record.probe = Probe(
                        status="retrying", code="rate_limit", attempt=attempt,
                        retry_seconds=seconds,
                    )
                    await sleep(seconds)
                    continue
                record.probe = Probe(
                    status="error", attempt=attempt,
                    code="unauthorized" if status == 401 else
                    "rate_limit" if status == 429 else "network",
                )
                break
    except asyncio.CancelledError:
        record.probe = Probe()
        raise
    except Exception:
        record.probe = Probe(status="error", code="network")
    finally:
        catalog.persist()
    return record
