"""Skill records: one folder, one `SKILL.md`, one description the model may see."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SkillSource = Literal["bundled", "user", "workspace"]
SkillCategory = Literal["coding", "tests", "web", "docs", "other"]
ScanStatus = Literal["clean", "flagged", "blocked"]


class SkillModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SkillScan(SkillModel):
    """What the pre-use scan found. `blocked` never reaches a model."""

    status: ScanStatus = "clean"
    findings: list[str] = Field(default_factory=list)
    scripts: list[str] = Field(default_factory=list)


class SkillRecord(SkillModel):
    name: str
    description: str
    command: str | None = None
    category: SkillCategory = "other"
    source: SkillSource = "bundled"
    path: str = ""
    """Where the folder lives, in the form the hub shows (never an absolute host path)."""
    enabled: bool = True
    requires_approval: bool = False
    tokens: int = Field(default=0, ge=0)
    scan: SkillScan = Field(default_factory=SkillScan)
    problem: str | None = None
    """Set when the folder exists but is not a usable skill; the hub lists it as broken."""


class SkillDetail(SkillRecord):
    body: str = ""
    references: list[str] = Field(default_factory=list)


class SkillsState(SkillModel):
    """`.harness/skills.json`: the person's per-workspace switches."""

    overrides: dict[str, bool] = Field(default_factory=dict)
    catalog_url: str | None = None


class SkillSummary(SkillModel):
    """The minimum that may enter the prompt."""

    name: str
    description: str
    command: str | None = None


class SkillCommand(SkillModel):
    command: str
    name: str
    description: str
    requires_approval: bool = False


class SkillsResponse(SkillModel):
    workspace: str
    skills: list[SkillRecord] = Field(default_factory=list)
    commands: list[SkillCommand] = Field(default_factory=list)
    catalog_url: str | None = None
    fetched_at: str | None = None
    problems: list[SkillRecord] = Field(default_factory=list)


class MarketplaceEntry(SkillModel):
    name: str
    description: str
    url: str
    command: str | None = None
    category: SkillCategory = "other"
    version: str | None = None
    author: str | None = None


class MarketplaceCatalog(SkillModel):
    version: Literal[1] = 1
    skills: list[MarketplaceEntry] = Field(default_factory=list)
    fetched_at: str | None = None
    catalog_url: str | None = None
    error: str | None = None


class SkillInstallInput(SkillModel):
    kind: Literal["folder", "zip", "git"]
    source: str = Field(min_length=1, max_length=2048)


class SkillEnabledInput(SkillModel):
    name: str = Field(min_length=1, max_length=64)
    enabled: bool


class SkillWriteInput(SkillModel):
    name: str = Field(min_length=1, max_length=64)
    description: str = Field(min_length=1, max_length=1024)
    body: str = Field(default="", max_length=32_000)
    command: str | None = Field(default=None, max_length=33)
    category: SkillCategory = "other"
    requires_approval: bool = False


class AgentRecord(SkillModel):
    name: str
    description: str
    source: Literal["workspace"] = "workspace"
    tools: list[str] = Field(default_factory=list)
    path: str = ""
    problem: str | None = None


class AgentDocument(SkillModel):
    record: AgentRecord
    instructions: str = ""


class AgentWriteInput(SkillModel):
    name: str = Field(min_length=1, max_length=64)
    description: str = Field(min_length=1, max_length=1024)
    instructions: str = Field(default="", max_length=32_000)
    tools: list[str] = Field(default_factory=list)


class MemoryDocument(SkillModel):
    workspace: str
    content: str = ""
    bytes: int = Field(default=0, ge=0)
    limit: int = Field(default=32_768, ge=1)


class McpTool(SkillModel):
    name: str
    namespaced: str
    description: str = ""
    input_schema: str = "{}"
    """The server's input schema, serialized. Never interpreted as code."""


class McpServer(SkillModel):
    name: str
    transport: Literal["stdio", "http"] = "stdio"
    command: list[str] | None = None
    url: str | None = None
    env_keys: list[str] = Field(default_factory=list)
    enabled: bool = True


class ConnectorStatus(SkillModel):
    name: str
    transport: Literal["stdio", "http"] = "stdio"
    display: str = ""
    """The command or URL, redacted, for the card."""
    enabled: bool = True
    status: Literal["connected", "error", "disabled"] = "disabled"
    tools: list[McpTool] = Field(default_factory=list)
    error: str | None = None


class ConnectorList(SkillModel):
    workspace: str
    servers: list[ConnectorStatus] = Field(default_factory=list)


class McpServerInput(SkillModel):
    name: str = Field(min_length=1, max_length=32)
    transport: Literal["stdio", "http"] = "stdio"
    command: str | None = Field(default=None, max_length=4096)
    url: str | None = Field(default=None, max_length=2048)
    env_keys: list[str] = Field(default_factory=list)
    enabled: bool = True


class CustomizeSettings(SkillModel):
    """The hub's read-only overview: counts and the workspace it describes."""

    workspace: str
    skills: int = Field(default=0, ge=0)
    enabled_skills: int = Field(default=0, ge=0)
    agents: int = Field(default=0, ge=0)
    servers: int = Field(default=0, ge=0)
    memory_bytes: int = Field(default=0, ge=0)
