"""A bounded MCP client: a handshake, a tool list, a call, and a failure that stays a card."""

import json
import sys
from pathlib import Path

import httpx
import pytest

from connectors.client import (
    HttpSession,
    McpError,
    StdioSession,
    connect,
    namespace,
    render,
    status,
    tool_from,
)
from connectors.config import McpServerConfig

WORKER = Path(__file__).with_name("mcp_worker.py")


def server(mode: str = "normal", name: str = "fixture") -> McpServerConfig:
    return McpServerConfig(name=name, command=[sys.executable, str(WORKER), mode])


def test_a_stdio_session_lists_and_calls_tools(tmp_path: Path) -> None:
    session = StdioSession(server(), tmp_path, timeout=10)
    try:
        tools = session.list_tools()
        assert [tool.name for tool in tools] == ["echo", "count"]
        assert tools[0].input_schema["required"] == ["text"]
        assert session.call("echo", {"text": "hi"}) == "echo: hi"
        assert session.call("missing", {}) == "Error: unknown tool"
    finally:
        session.close()


def test_a_server_that_exits_before_answering_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(McpError):
        StdioSession(server("exit"), tmp_path, timeout=5)


def test_a_silent_server_times_out(tmp_path: Path) -> None:
    with pytest.raises(McpError, match="timed out"):
        StdioSession(server("silent"), tmp_path, timeout=0.5)


def test_a_refused_handshake_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(McpError, match="no"):
        StdioSession(server("broken"), tmp_path, timeout=5)


def test_a_missing_binary_is_an_error(tmp_path: Path) -> None:
    broken = McpServerConfig(name="gone", command=["definitely-not-installed-binary"])
    with pytest.raises(McpError, match="could not be started"):
        connect(broken, tmp_path)


def test_status_wraps_a_failure_as_a_card(tmp_path: Path) -> None:
    broken = McpServerConfig(name="gone", command=["definitely-not-installed-binary"])
    found = status(broken, tmp_path)
    assert found.status == "error"
    assert found.error
    assert found.tools == []


def test_a_disabled_server_is_never_started(tmp_path: Path) -> None:
    off = McpServerConfig(
        name="gone", command=["definitely-not-installed-binary"], enabled=False
    )
    found = status(off, tmp_path)
    assert found.status == "disabled"
    assert found.enabled is False
    assert found.error is None


def test_status_namespaces_every_tool(tmp_path: Path) -> None:
    found = status(server(), tmp_path, timeout=10)
    assert found.status == "connected"
    assert [tool.namespaced for tool in found.tools] == ["fixture__echo", "fixture__count"]
    assert json.loads(found.tools[0].input_schema)["type"] == "object"
    assert "python" in found.display or "mcp_worker" in found.display


def test_an_http_session_speaks_streamable_http(tmp_path: Path) -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        method = str(payload.get("method"))
        if "id" not in payload:
            return httpx.Response(202, headers={"mcp-session-id": "s1"})
        seen.append(method)
        results: dict[str, dict[str, object]] = {
            "initialize": {"protocolVersion": "2025-06-18", "capabilities": {}},
            "tools/list": {"tools": [{"name": "ping", "description": "Ping."}]},
            "tools/call": {"content": [{"type": "text", "text": "pong"}]},
        }
        return httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": payload["id"], "result": results[method]},
            headers={"Mcp-Session-Id": "s1"},
        )

    remote = McpServerConfig(name="remote", transport="http", url="https://x.test/mcp")
    session = HttpSession(remote, timeout=5, transport=httpx.MockTransport(handler))
    try:
        assert [tool.name for tool in session.list_tools()] == ["ping"]
        assert session.call("ping", {}) == "pong"
        assert session.session_id == "s1"
    finally:
        session.close()
    assert seen[:3] == ["initialize", "tools/list", "tools/call"]


def test_an_http_event_stream_is_read() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        body = {"jsonrpc": "2.0", "id": payload.get("id"), "result": {"tools": []}}
        return httpx.Response(
            200,
            text=f"event: message\ndata: {json.dumps(body)}\n\n",
            headers={"Content-Type": "text/event-stream"},
        )

    remote = McpServerConfig(name="remote", transport="http", url="https://x.test/mcp")
    session = HttpSession(remote, timeout=5, transport=httpx.MockTransport(handler))
    try:
        assert session.list_tools() == []
    finally:
        session.close()


def test_an_http_error_status_is_an_error() -> None:
    remote = McpServerConfig(name="remote", transport="http", url="https://x.test/mcp")
    with pytest.raises(McpError, match="500"):
        HttpSession(
            remote,
            timeout=5,
            transport=httpx.MockTransport(lambda request: httpx.Response(500)),
        )


def test_names_are_namespaced_once() -> None:
    assert namespace("files", "read") == "files__read"


def test_content_blocks_are_flattened() -> None:
    blocks = {"content": [{"type": "text", "text": "a"}, {"type": "image"}]}
    assert render(blocks) == "a\n[image content]"
    assert render({"content": [{"type": "text", "text": "bad"}], "isError": True}) == "Error: bad"


def test_a_tool_without_a_name_is_dropped() -> None:
    assert tool_from({"description": "nameless"}) is None
    assert tool_from("not a dict") is None
    assert tool_from({"name": "x" * 65}) is None
    assert tool_from({"name": "ok", "inputSchema": {"type": "object"}}) is not None
