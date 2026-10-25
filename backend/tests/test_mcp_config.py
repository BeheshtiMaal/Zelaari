"""`.harness/mcp.json` is a capability grant: names, transports, and env *names* only."""

import json
from pathlib import Path

import pytest

from connectors.config import (
    McpFile,
    McpServerConfig,
    command_parts,
    environment,
    load,
    merged,
)
from tools.jail import storage_path


def test_a_stdio_server_needs_a_command() -> None:
    with pytest.raises(ValueError, match="needs a command"):
        McpServerConfig(name="files", transport="stdio")
    server = McpServerConfig(name="files", command=["node", "server.js"])
    assert server.enabled is True


def test_a_stdio_server_cannot_carry_a_url() -> None:
    with pytest.raises(ValueError, match="no URL"):
        McpServerConfig(
            name="files", transport="stdio", command=["node", "server.js"], url="https://x.test"
        )


def test_an_http_server_needs_https_and_no_command() -> None:
    with pytest.raises(ValueError, match="https"):
        McpServerConfig(name="remote", transport="http", url="http://x.test/mcp")
    with pytest.raises(ValueError, match="no command"):
        McpServerConfig(
            name="remote", transport="http", url="https://x.test/mcp", command=["node"]
        )
    assert McpServerConfig(name="remote", transport="http", url="https://x.test/mcp").transport


def test_names_are_bounded_and_predictable() -> None:
    with pytest.raises(ValueError, match="lowercase"):
        McpServerConfig(name="Files Server", command=["node"])
    with pytest.raises(ValueError, match="lowercase"):
        McpServerConfig(name="files_server", command=["node"])
    assert McpServerConfig(name="a" * 32, command=["node"]).name == "a" * 32


def test_environment_holds_names_never_values() -> None:
    with pytest.raises(ValueError, match="names, not values"):
        McpServerConfig(name="files", command=["node"], env_keys=["TOKEN=secret"])
    server = McpServerConfig(name="files", command=["node"], env_keys=["TOKEN"])
    values = environment(server, {"TOKEN": "abc", "PATH": "/bin", "SECRET": "no"})
    assert values == {"TOKEN": "abc", "PATH": "/bin"}
    assert "SECRET" not in values


def test_a_missing_variable_is_simply_absent() -> None:
    server = McpServerConfig(name="files", command=["node"], env_keys=["TOKEN"])
    assert environment(server, {"PATH": "/bin"}) == {"PATH": "/bin"}


def test_the_file_rejects_duplicates_and_a_flood() -> None:
    server = McpServerConfig(name="files", command=["node"])
    with pytest.raises(ValueError, match="unique"):
        McpFile(servers=[server, server])
    with pytest.raises(ValueError, match="At most 32"):
        McpFile(
            servers=[
                McpServerConfig(name=f"s{index}", command=["node"]) for index in range(33)
            ]
        )


def test_merged_writes_only_version_and_servers() -> None:
    text = merged([McpServerConfig(name="files", command=["node", "server.js"])])
    document = McpFile.model_validate_json(text)
    assert [server.name for server in document.servers] == ["files"]
    assert json.loads(text) == {
        "version": 1,
        "servers": [
            {
                "name": "files",
                "transport": "stdio",
                "command": ["node", "server.js"],
                "url": None,
                "env_keys": [],
                "enabled": True,
            }
        ],
    }


def test_a_damaged_file_reads_as_empty(tmp_path: Path) -> None:
    path = storage_path(tmp_path, "mcp.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")
    assert load(tmp_path).servers == []


def test_a_command_line_becomes_argv() -> None:
    parts = command_parts('node "server file.js" --root .')
    assert parts == ["node", "server file.js", "--root", "."]
    with pytest.raises(ValueError, match="unbalanced"):
        command_parts('node "server.js')
