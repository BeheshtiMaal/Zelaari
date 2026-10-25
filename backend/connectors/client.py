"""A bounded MCP client: JSON-RPC 2.0 over stdio or streamable HTTP.

No SDK: the protocol surface a coding agent needs is `initialize`, `tools/list` and
`tools/call`, and owning it keeps the packaged engine small and the timeout behaviour the
same as every other process the engine starts.
"""

import json
import os
import queue
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import httpx

from connectors.config import McpServerConfig, environment
from skills.types import ConnectorStatus, McpTool

PROTOCOL_VERSION = "2025-06-18"
TIMEOUT = 5.0
MAX_LINE_BYTES = 512_000
MAX_TOOLS = 64
CLIENT = {"name": "CodeHarness", "version": "0.1.0"}


class McpError(Exception):
    """A server that could not start, answer in time, or answer at all."""


@dataclass
class ToolSpec:
    name: str
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)


class Session(Protocol):
    def list_tools(self) -> list[ToolSpec]: ...
    def call(self, name: str, arguments: dict[str, Any]) -> str: ...
    def close(self) -> None: ...


def tool_from(payload: object) -> ToolSpec | None:
    if not isinstance(payload, dict):
        return None
    name = payload.get("name")
    if not isinstance(name, str) or not name or len(name) > 64:
        return None
    description = payload.get("description")
    schema = payload.get("inputSchema")
    return ToolSpec(
        name=name,
        description=" ".join(description.split())[:2000] if isinstance(description, str) else "",
        input_schema=schema if isinstance(schema, dict) else {},
    )


def render(result: object) -> str:
    """Flatten MCP content blocks into text; anything unknown is described, not guessed."""
    if not isinstance(result, dict):
        return json.dumps(result, ensure_ascii=False)[:MAX_LINE_BYTES]
    blocks = result.get("content")
    if not isinstance(blocks, list):
        return json.dumps(result, ensure_ascii=False)[:MAX_LINE_BYTES]
    parts: list[str] = []
    for block in blocks:
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text")
            if isinstance(text, str):
                parts.append(text)
        elif isinstance(block, dict) and isinstance(block.get("type"), str):
            parts.append(f"[{block['type']} content]")
    text = "\n".join(parts) or json.dumps(result, ensure_ascii=False)
    if result.get("isError") is True:
        return f"Error: {text}"
    return text[:MAX_LINE_BYTES]


class StdioSession:
    def __init__(self, server: McpServerConfig, root: Path, timeout: float = TIMEOUT) -> None:
        if not server.command:
            raise McpError("This server has no command")
        self.name = server.name
        self.timeout = timeout
        self.lines: queue.Queue[str | None] = queue.Queue()
        self.next_id = 0
        self.job: Any = None
        creation = 0
        if sys.platform == "win32":
            from tools.jobobject import CREATE_NO_WINDOW, JobObject

            creation = CREATE_NO_WINDOW
            try:
                self.job = JobObject()
            except OSError:
                self.job = None
        try:
            self.process = subprocess.Popen(  # noqa: S603 - argv is the person's configured server
                server.command,
                cwd=str(root),
                env=environment(server, dict(os.environ)),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=creation,
            )
        except OSError:
            raise McpError("The server command could not be started") from None
        if self.job is not None:
            try:
                self.job.assign(self.process.pid)
            except OSError:
                self.job = None
        threading.Thread(target=self._read, daemon=True).start()
        threading.Thread(target=self._drain, daemon=True).start()
        try:
            self.initialize()
        except McpError:
            # A server that never finishes the handshake must not outlive this attempt.
            self.close()
            raise

    def _read(self) -> None:
        assert self.process.stdout is not None
        for line in self.process.stdout:
            if len(line) > MAX_LINE_BYTES:
                continue
            self.lines.put(line)
        self.lines.put(None)

    def _drain(self) -> None:
        assert self.process.stderr is not None
        for _ in self.process.stderr:
            pass

    def _write(self, payload: dict[str, Any]) -> None:
        if self.process.stdin is None or self.process.poll() is not None:
            raise McpError("The server exited")
        try:
            self.process.stdin.write(json.dumps(payload) + "\n")
            self.process.stdin.flush()
        except (OSError, ValueError):
            raise McpError("The server stopped reading") from None

    def _request(self, method: str, params: dict[str, Any]) -> object:
        self.next_id += 1
        identifier = self.next_id
        self._write({"jsonrpc": "2.0", "id": identifier, "method": method, "params": params})
        deadline = time.monotonic() + self.timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise McpError(f"{method} timed out after {self.timeout:g}s")
            try:
                line = self.lines.get(timeout=remaining)
            except queue.Empty:
                raise McpError(f"{method} timed out after {self.timeout:g}s") from None
            if line is None:
                raise McpError("The server exited before answering")
            try:
                message = json.loads(line)
            except ValueError:
                continue
            if not isinstance(message, dict) or message.get("id") != identifier:
                continue
            error = message.get("error")
            if isinstance(error, dict):
                raise McpError(str(error.get("message") or "The server returned an error"))
            return message.get("result")

    def initialize(self) -> None:
        self._request(
            "initialize",
            {"protocolVersion": PROTOCOL_VERSION, "capabilities": {}, "clientInfo": CLIENT},
        )
        self._write({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def list_tools(self) -> list[ToolSpec]:
        result = self._request("tools/list", {})
        tools = result.get("tools") if isinstance(result, dict) else None
        if not isinstance(tools, list):
            return []
        found = [tool_from(item) for item in tools[:MAX_TOOLS]]
        return [item for item in found if item is not None]

    def call(self, name: str, arguments: dict[str, Any]) -> str:
        return render(self._request("tools/call", {"name": name, "arguments": arguments}))

    def close(self) -> None:
        try:
            if self.process.stdin is not None:
                self.process.stdin.close()
        except OSError:
            pass
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
        if self.job is not None:
            self.job.close()
            self.job = None


class HttpSession:
    def __init__(
        self,
        server: McpServerConfig,
        timeout: float = TIMEOUT,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not server.url:
            raise McpError("This server has no URL")
        self.url = server.url
        self.timeout = timeout
        self.next_id = 0
        self.session_id: str | None = None
        self.client = httpx.Client(
            timeout=timeout,
            transport=transport,
            headers={
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
            },
        )
        try:
            self.initialize()
        except McpError:
            self.client.close()
            raise

    def _post(self, payload: dict[str, Any]) -> httpx.Response:
        headers = {"Mcp-Session-Id": self.session_id} if self.session_id else {}
        try:
            response = self.client.post(self.url, json=payload, headers=headers)
        except httpx.HTTPError as error:
            raise McpError(f"The server request failed ({type(error).__name__})") from None
        if response.status_code >= 400:
            raise McpError(f"The server answered {response.status_code}")
        session = response.headers.get("mcp-session-id")
        if session:
            self.session_id = session
        return response

    def _payload(self, response: httpx.Response) -> object:
        if "text/event-stream" in response.headers.get("content-type", ""):
            for line in reversed(response.text.splitlines()):
                if line.startswith("data:"):
                    try:
                        return json.loads(line[5:].strip())
                    except ValueError:
                        continue
            raise McpError("The server sent no readable event")
        try:
            return response.json()
        except ValueError:
            raise McpError("The server did not return JSON") from None

    def _request(self, method: str, params: dict[str, Any]) -> object:
        self.next_id += 1
        message = self._payload(
            self._post({"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params})
        )
        if not isinstance(message, dict):
            raise McpError("The server returned an unexpected message")
        error = message.get("error")
        if isinstance(error, dict):
            raise McpError(str(error.get("message") or "The server returned an error"))
        return message.get("result")

    def initialize(self) -> None:
        self._request(
            "initialize",
            {"protocolVersion": PROTOCOL_VERSION, "capabilities": {}, "clientInfo": CLIENT},
        )
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def list_tools(self) -> list[ToolSpec]:
        result = self._request("tools/list", {})
        tools = result.get("tools") if isinstance(result, dict) else None
        if not isinstance(tools, list):
            return []
        found = [tool_from(item) for item in tools[:MAX_TOOLS]]
        return [item for item in found if item is not None]

    def call(self, name: str, arguments: dict[str, Any]) -> str:
        return render(self._request("tools/call", {"name": name, "arguments": arguments}))

    def close(self) -> None:
        self.client.close()


def connect(
    server: McpServerConfig,
    root: Path,
    timeout: float = TIMEOUT,
    transport: httpx.BaseTransport | None = None,
) -> Session:
    if server.transport == "http":
        return HttpSession(server, timeout=timeout, transport=transport)
    return StdioSession(server, root, timeout=timeout)


def namespace(server: str, tool: str) -> str:
    return f"{server}__{tool}"


def status(
    server: McpServerConfig,
    root: Path,
    timeout: float = TIMEOUT,
    transport: httpx.BaseTransport | None = None,
) -> ConnectorStatus:
    """Connect, list, disconnect. A failure becomes a card, never an exception."""
    display = " ".join(server.command or []) if server.command else (server.url or "")
    if not server.enabled:
        return ConnectorStatus(
            name=server.name,
            transport=server.transport,
            display=display,
            enabled=False,
            status="disabled",
        )
    session: Session | None = None
    try:
        session = connect(server, root, timeout, transport)
        tools = [
            McpTool(
                name=item.name,
                namespaced=namespace(server.name, item.name),
                description=item.description,
                input_schema=json.dumps(item.input_schema, ensure_ascii=False),
            )
            for item in session.list_tools()
        ]
        return ConnectorStatus(
            name=server.name,
            transport=server.transport,
            display=display,
            enabled=True,
            status="connected",
            tools=tools,
        )
    except (McpError, OSError, ValueError) as error:
        return ConnectorStatus(
            name=server.name,
            transport=server.transport,
            display=display,
            enabled=True,
            status="error",
            error=str(error)[:500],
        )
    finally:
        if session is not None:
            session.close()
