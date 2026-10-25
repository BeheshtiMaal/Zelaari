"""MCP tools as ordinary LangChain tools, namespaced and schema-checked.

A server's JSON Schema becomes a small Pydantic model, so an edited argument is validated
exactly like a built-in tool's. The permission layer sees the name, not the server.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, create_model

from connectors.client import TIMEOUT, McpError, Session, ToolSpec, connect, namespace
from connectors.config import McpServerConfig

NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]{0,63}$")
MAX_PROPERTIES = 32
TYPES: dict[str, Any] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list[Any],
    "object": dict[str, Any],
}


def arguments_model(name: str, spec: ToolSpec) -> type[BaseModel]:
    properties = spec.input_schema.get("properties")
    required = spec.input_schema.get("required")
    fields: dict[str, Any] = {}
    if isinstance(properties, dict):
        for key, value in list(properties.items())[:MAX_PROPERTIES]:
            if not isinstance(key, str) or not NAME.match(key):
                continue
            kind = value.get("type") if isinstance(value, dict) else None
            annotation = TYPES.get(kind, Any) if isinstance(kind, str) else Any
            needed = isinstance(required, list) and key in required
            fields[key] = (annotation, ... if needed else None)
    return create_model(f"{name}_arguments", **fields)


def tool_for(session: Session, server: str, spec: ToolSpec) -> BaseTool:
    full = namespace(server, spec.name)
    model = arguments_model(full, spec)

    def invoke(**kwargs: Any) -> str:
        try:
            return session.call(spec.name, kwargs)
        except McpError as error:
            return f"Error: {error}"

    return StructuredTool.from_function(
        func=invoke,
        name=full,
        description=spec.description or f"{spec.name} on the {server} MCP server.",
        args_schema=model,
    )


@dataclass
class Connectors:
    """One run's live sessions. `close` is the caller's job, in a finally block."""

    sessions: list[Session] = field(default_factory=list)
    tools: list[BaseTool] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)

    def close(self) -> None:
        for session in self.sessions:
            try:
                session.close()
            except OSError:
                continue
        self.sessions.clear()


def build(
    root: Path, servers: list[McpServerConfig], timeout: float = TIMEOUT
) -> Connectors:
    """Connect what can be connected; a broken server costs its own tools only."""
    found = Connectors()
    for server in servers:
        if not server.enabled:
            continue
        try:
            session = connect(server, root, timeout)
        except (McpError, OSError, ValueError) as error:
            found.errors[server.name] = str(error)[:500]
            continue
        found.sessions.append(session)
        try:
            for spec in session.list_tools():
                found.tools.append(tool_for(session, server.name, spec))
        except (McpError, OSError, ValueError) as error:
            found.errors[server.name] = str(error)[:500]
    return found
