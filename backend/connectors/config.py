"""`.harness/mcp.json`: names, transports and environment *names*, never values.

A server entry is a command to run or a URL to call. Both are capability grants, so both
are written only through the protected-configuration approval.
"""

import json
import re
import shlex
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tools.jail import storage_path

NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")
ENV_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
MAX_SERVERS = 32
MAX_ARGUMENTS = 8
MAX_ARGUMENT = 512
MAX_ENV_KEYS = 16


class ConnectorModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class McpServerConfig(ConnectorModel):
    name: str
    transport: Literal["stdio", "http"] = "stdio"
    command: list[str] | None = None
    url: str | None = None
    env_keys: list[str] = Field(default_factory=list)
    enabled: bool = True

    @model_validator(mode="after")
    def consistent(self) -> "McpServerConfig":
        if not NAME.match(self.name):
            raise ValueError("A server name is lowercase letters, digits or dashes (max 32)")
        if self.transport == "stdio":
            if not self.command:
                raise ValueError("A stdio server needs a command")
            if len(self.command) > MAX_ARGUMENTS + 1:
                raise ValueError(f"A stdio command is limited to {MAX_ARGUMENTS + 1} parts")
            if any(not part or len(part) > MAX_ARGUMENT for part in self.command):
                raise ValueError("A command part is empty or too long")
            if self.url:
                raise ValueError("A stdio server has no URL")
        else:
            if not self.url or not self.url.startswith("https://"):
                raise ValueError("An http server needs an https URL")
            if self.command:
                raise ValueError("An http server has no command")
        if len(self.env_keys) > MAX_ENV_KEYS:
            raise ValueError(f"At most {MAX_ENV_KEYS} environment names are allowed")
        for key in self.env_keys:
            if not ENV_KEY.match(key):
                raise ValueError("env_keys holds environment variable names, not values")
        return self


class McpFile(ConnectorModel):
    version: Literal[1] = 1
    servers: list[McpServerConfig] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique(self) -> "McpFile":
        if len(self.servers) > MAX_SERVERS:
            raise ValueError(f"At most {MAX_SERVERS} servers are supported")
        names = [server.name for server in self.servers]
        if len(set(names)) != len(names):
            raise ValueError("Server names must be unique")
        return self


def load(root: Path) -> McpFile:
    path = storage_path(root, "mcp.json")
    try:
        if not path.is_file():
            return McpFile()
        return McpFile.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return McpFile()


def merged(servers: list[McpServerConfig]) -> str:
    """The reviewed bytes are exactly `version` and `servers`; nothing else is carried.

    `.harness/mcp.json` is engine storage with one purpose, so an unknown key is dropped
    rather than preserved: the document a person approves must be the document validated.
    """
    document = {
        "version": 1,
        "servers": [server.model_dump(mode="json") for server in servers],
    }
    return json.dumps(document, ensure_ascii=False, indent=2)


def command_parts(value: str) -> list[str]:
    """A single-line command from the form into argv, quotes respected, nothing invented."""
    try:
        parts = shlex.split(value, posix=False)
    except ValueError:
        raise ValueError("The command has an unbalanced quote") from None
    cleaned = [part.strip().strip('"').strip("'") for part in parts]
    return [part for part in cleaned if part]


def environment(server: McpServerConfig, source: dict[str, str]) -> dict[str, str]:
    """Only the names the person listed, and only if they exist in the process."""
    values = {"SystemRoot": source.get("SystemRoot", ""), "PATH": source.get("PATH", "")}
    for key in server.env_keys:
        if key in source:
            values[key] = source[key]
    return {key: value for key, value in values.items() if value}
