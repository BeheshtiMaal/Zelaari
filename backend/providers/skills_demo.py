"""Offline runs for the Customize surfaces: one skill load, one search, one MCP call.

Each behaviour is a single real tool call followed by a plain answer, so the walkthrough
exercises the actual `load_skill` tool, the actual search client and the actual connector
tool rather than a description of them. The task text is the only input: nothing here
knows what the workspace contains.
"""

import json
import re

from langchain_core.messages import AIMessage, ToolMessage

SKILL = re.compile(r"demo skill load ([\w-]+)\s*$")
SEARCH = re.compile(r"demo web search (.+)$", re.DOTALL)
MCP = re.compile(r"demo mcp call ([\w-]+__[\w-]+)\s*$")


def called(results: list[ToolMessage], name: str) -> bool:
    return any(message.name == name for message in results)


def demo_customize(task: str, results: list[ToolMessage]) -> AIMessage | None:
    """Return the next scripted turn, or `None` when this is not a Customize run."""
    skill = SKILL.search(task)
    if skill:
        name = skill.group(1)
        if not called(results, "load_skill"):
            return AIMessage(
                content="",
                tool_calls=[
                    {"name": "load_skill", "id": "demo-load", "args": {"name": name}}
                ],
            )
        body = str(results[-1].content)
        return AIMessage(
            content=(
                'root = Stack([Callout("خواندن مهارت پایان یافت"), '
                f'KeyValue("حجم بدنه", {json.dumps(f"{len(body)} chars")})]);'
            )
        )

    search = SEARCH.search(task)
    if search:
        if not called(results, "web_search"):
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "web_search",
                        "id": "demo-search",
                        "args": {"query": search.group(1).strip(), "limit": 3},
                    }
                ],
            )
        payload = json.loads(str(results[-1].content))
        found = payload.get("results") or []
        source = found[0]["url"] if found else payload.get("error", "")
        return AIMessage(
            content=(
                'root = Stack([Callout("جست‌وجو پایان یافت"), '
                f'KeyValue("منبع", {json.dumps(source)})]);'
            )
        )

    mcp = MCP.search(task)
    if mcp:
        name = mcp.group(1)
        if not called(results, name):
            return AIMessage(
                content="",
                tool_calls=[{"name": name, "id": "demo-mcp", "args": {"text": "ping"}}],
            )
        return AIMessage(
            content=(
                'root = Stack([Callout("ابزار بیرونی پاسخ داد"), '
                f'KeyValue("نتیجه", {json.dumps(str(results[-1].content)[:200])})]);'
            )
        )
    return None
