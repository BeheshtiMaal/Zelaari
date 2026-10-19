"""Tool contracts: command results, file listings and snapshot metadata."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from permissions.types import RiskLevel


class ToolModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CommandResult(ToolModel):
    """What `run_command` returns to the model and what the timeout card reads."""

    command: str
    shell: Literal["powershell", "cmd"]
    exit_code: int | None = None
    duration_ms: int = Field(default=0, ge=0)
    output: str = ""
    truncated: bool = False
    total_lines: int = Field(default=0, ge=0)
    offset: int = Field(default=0, ge=0)
    timed_out: bool = False
    timeout_seconds: float = Field(default=120, gt=0)
    killed_tree: bool = False


class FileEntry(ToolModel):
    name: str
    path: str
    kind: Literal["file", "dir"]
    size: int = Field(default=0, ge=0)
    changed: bool = False


class FileContent(ToolModel):
    path: str
    text: str
    binary: bool = False
    truncated: bool = False
    changed_lines: list[tuple[int, int]] = Field(default_factory=list)
    """Inclusive 1-based ranges that differ from the newest snapshot of this path."""

    pending_approval: bool = False


class FileListing(ToolModel):
    """`GET /files?path=` returns a directory listing or a file, never both."""

    path: str
    kind: Literal["file", "dir"]
    entries: list[FileEntry] = Field(default_factory=list)
    file: FileContent | None = None


class SnapshotMeta(ToolModel):
    id: str
    path: str
    existed: bool
    ts: str
    run_id: str | None = None
    call_id: str | None = None
    bytes: int = Field(default=0, ge=0)
    tool: str = ""


class SnapshotEntry(SnapshotMeta):
    pass


class RevertResult(ToolModel):
    path: str
    snapshot_id: str
    created_snapshot_id: str


class BranchSwitch(ToolModel):
    workspace: str
    branch: str


class BranchSwitchResult(ToolModel):
    branch: str | None = None
    error: str | None = None


class RulesResponse(ToolModel):
    mode: Literal["read-only", "ask", "auto"]
    tools: dict[str, list[dict[str, str]]] = Field(default_factory=dict)
    defaults: dict[str, str] = Field(default_factory=dict)
    always_ask: list[str] = Field(default_factory=list)


class RiskLabel(ToolModel):
    level: RiskLevel
    reasons: list[str] = Field(default_factory=list)
