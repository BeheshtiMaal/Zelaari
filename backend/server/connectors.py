"""MCP connectors: what is configured, what answers, and what a change would do.

Every mutation is a capability grant — a server is a command to run or a URL to call — so
all four writes go through the protected-configuration approval. `test` deliberately reads
only servers that are already stored and approved; it never executes a value from a form
that has not been reviewed.
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import APIRouter, HTTPException

from connectors import client
from connectors.config import MAX_SERVERS, McpServerConfig, command_parts, load
from permissions.types import ApprovalRecord
from skills.types import ConnectorList, ConnectorStatus, McpServerInput
from store.actions import ActionApprovals
from tools.jail import JailError, workspace_root

WORKERS = 4


def _root(value: str) -> Path:
    try:
        return workspace_root(value)
    except (JailError, ValueError, OSError):
        raise HTTPException(400, "Select an accessible workspace") from None


def server_from(value: McpServerInput) -> McpServerConfig:
    """A form line into an argv. Quotes are respected; nothing is invented."""
    command: list[str] | None = None
    if value.transport == "stdio":
        if not value.command or not value.command.strip():
            raise ValueError("A stdio server needs a command")
        command = command_parts(value.command)
    try:
        return McpServerConfig(
            name=value.name,
            transport=value.transport,
            command=command,
            url=value.url.strip() if value.url else None,
            env_keys=[key.strip() for key in value.env_keys if key.strip()],
            enabled=value.enabled,
        )
    except ValueError as error:
        raise ValueError(_message(error)) from None


def _message(error: Exception) -> str:
    """Pydantic prefixes validation errors with a location; the person needs the sentence."""
    text = str(error)
    marker = "Value error, "
    index = text.find(marker)
    return text[index + len(marker) :].splitlines()[0] if index >= 0 else text


def statuses(root: Path, servers: list[McpServerConfig]) -> list[ConnectorStatus]:
    """Connect in parallel so one silent server cannot hold the screen for its own timeout."""
    if not servers:
        return []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        return list(pool.map(lambda item: client.status(item, root), servers))


def connectors_routes(actions: ActionApprovals) -> APIRouter:
    router = APIRouter()

    @router.get("/connectors")
    def list_connectors(workspace: str) -> ConnectorList:
        root = _root(workspace)
        return ConnectorList(workspace=str(root), servers=statuses(root, load(root).servers))

    @router.post("/connectors", status_code=202)
    def add_connector(workspace: str, value: McpServerInput) -> ApprovalRecord:
        root = _root(workspace)
        current = load(root).servers
        if any(server.name == value.name for server in current):
            raise HTTPException(409, "A server with this name already exists")
        if len(current) >= MAX_SERVERS:
            raise HTTPException(409, f"At most {MAX_SERVERS} servers are supported")
        try:
            server = server_from(value)
            return actions.propose_mcp(
                root,
                [*current, server],
                tool="mcp_server_add",
                name=server.name,
                reason=f"Run and expose the {server.name} MCP server's tools to the agent",
            )
        except (OSError, ValueError) as error:
            raise HTTPException(409, _message(error)) from None

    @router.put("/connectors/{name}", status_code=202)
    def update_connector(workspace: str, name: str, value: McpServerInput) -> ApprovalRecord:
        if name != value.name:
            raise HTTPException(400, "The name in the body must match the path")
        root = _root(workspace)
        current = load(root).servers
        if not any(server.name == name for server in current):
            raise HTTPException(404, "Unknown MCP server")
        try:
            server = server_from(value)
            servers = [server if item.name == name else item for item in current]
            return actions.propose_mcp(
                root,
                servers,
                tool="mcp_server_update",
                name=name,
                reason=f"Change how the {name} MCP server is started or enabled",
            )
        except (OSError, ValueError) as error:
            raise HTTPException(409, _message(error)) from None

    @router.delete("/connectors/{name}", status_code=202)
    def delete_connector(workspace: str, name: str) -> ApprovalRecord:
        root = _root(workspace)
        current = load(root).servers
        servers = [item for item in current if item.name != name]
        if len(servers) == len(current):
            raise HTTPException(404, "Unknown MCP server")
        try:
            return actions.propose_mcp(
                root,
                servers,
                tool="mcp_server_delete",
                name=name,
                reason=f"Stop running the {name} MCP server and remove its tools",
            )
        except (OSError, ValueError) as error:
            raise HTTPException(409, _message(error)) from None

    @router.post("/connectors/{name}/test")
    def test_connector(workspace: str, name: str) -> ConnectorStatus:
        """Only a stored server is started: an unreviewed form value is never executed."""
        root = _root(workspace)
        found = next((item for item in load(root).servers if item.name == name), None)
        if found is None:
            raise HTTPException(404, "Unknown MCP server")
        return client.status(found, root)

    return router
