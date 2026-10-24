"""Bounded workspace settings for verification, context and the terminal.

The mock's defaults are the product defaults. A missing or unreadable file yields those
defaults, so a damaged workspace never stops a run; only a save needs a readable document.
"""

import json
from pathlib import Path
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)

from tools.jail import storage_path
from verify.detection import Detection, detect

MAX_CONFIG_BYTES = 1_000_000
Command = Annotated[str, StringConstraints(strip_whitespace=True, max_length=400)]


class VerifyModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ContextSettings(VerifyModel):
    compaction_percent: int = Field(default=60, ge=30, le=90, strict=True)
    keep_messages: int = Field(default=8, ge=0, le=50, strict=True)
    offload: bool = Field(default=True, strict=True)
    show_ring: bool = Field(default=True, strict=True)


class VerifySettings(VerifyModel):
    gate: bool = Field(default=True, strict=True)
    command: Command | None = None
    max_steps: int = Field(default=40, ge=1, le=200, strict=True)
    max_minutes: int = Field(default=30, ge=1, le=240, strict=True)
    fix_attempts: int = Field(default=3, ge=0, le=10, strict=True)

    @field_validator("command", mode="before")
    @classmethod
    def blank_is_auto(cls, value: object) -> object:
        # The settings form sends an empty box for "auto"; that is not a command.
        if isinstance(value, str) and not value.strip():
            return None
        return value


class TerminalSettings(VerifyModel):
    shell: str = Field(default="auto", pattern=r"^(auto|powershell|cmd)$")
    timeout_seconds: int = Field(default=120, ge=1, le=600, strict=True)
    max_output_lines: int = Field(default=200, ge=20, le=2000, strict=True)


class VerifyConfig(VerifyModel):
    context: ContextSettings = Field(default_factory=ContextSettings)
    verify: VerifySettings = Field(default_factory=VerifySettings)
    terminal: TerminalSettings = Field(default_factory=TerminalSettings)


class VerifySettingsResponse(VerifyConfig):
    detection: Detection = Field(default_factory=Detection)


def read_document(root: Path) -> dict[str, Any]:
    """The raw config object. Raises only when a save would corrupt an existing file."""
    path = storage_path(root, "config.json")
    if not path.exists():
        return {}
    raw = path.read_bytes()
    if len(raw) > MAX_CONFIG_BYTES:
        raise ValueError("Workspace config is too large")
    document = json.loads(raw)
    if not isinstance(document, dict):
        raise ValueError("Workspace config must be an object")
    return document


def section(document: dict[str, Any], key: str) -> dict[str, Any]:
    value = document.get(key)
    return value if isinstance(value, dict) else {}


def load_config(root: Path) -> VerifyConfig:
    """Defaults survive a corrupt file; each section falls back on its own."""
    try:
        document = read_document(root)
    except (OSError, ValueError):
        return VerifyConfig()
    try:
        context = ContextSettings.model_validate(section(document, "context"))
    except ValueError:
        context = ContextSettings()
    try:
        verify = VerifySettings.model_validate(section(document, "verify"))
    except ValueError:
        verify = VerifySettings()
    try:
        terminal = TerminalSettings.model_validate(section(document, "terminal"))
    except ValueError:
        terminal = TerminalSettings()
    return VerifyConfig(context=context, verify=verify, terminal=terminal)


def merged_config(root: Path, config: VerifyConfig) -> str:
    """Rewrite only our three sections; every other key stays byte-identical."""
    document = read_document(root)
    document.update(config.model_dump(mode="json"))
    return json.dumps(document, ensure_ascii=False, indent=2)


def response(root: Path, config: VerifyConfig) -> VerifySettingsResponse:
    return VerifySettingsResponse(
        **config.model_dump(mode="json"), detection=detect(root, config.verify.command)
    )
