"""Public provider/settings contracts contain no credentials."""

from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ModelInput(Record):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    name: str = Field(min_length=1, max_length=120)
    base_url: str
    model: str = Field(min_length=1, max_length=200)

    @field_validator("base_url")
    @classmethod
    def endpoint(cls, value: str) -> str:
        url = urlsplit(value)
        if url.scheme not in {"https", "http"} or not url.hostname:
            raise ValueError("Use an HTTP(S) Base URL")
        if url.username or url.password or url.query or url.fragment:
            raise ValueError("Credentials, query and fragment are not allowed in Base URL")
        return value.rstrip("/")


def infer_kind(base_url: str) -> Literal["anthropic", "openai-compatible"]:
    if urlsplit(base_url).hostname == "api.anthropic.com":
        return "anthropic"
    return "openai-compatible"


class Context(Record):
    tokens: int = Field(default=32768, gt=0)
    source: Literal["metadata", "table", "error", "fallback"] = "fallback"
    estimated: bool = True


class Probe(Record):
    status: Literal["untested", "testing", "retrying", "ok", "error"] = "untested"
    code: Literal["unauthorized", "rate_limit", "no_tools", "network", "vault"] | None = None
    attempt: int = 0
    retry_seconds: float = 0


class ProviderRecord(Record):
    id: str = "demo"
    name: str
    model: str
    kind: Literal["demo", "openai-compatible", "anthropic"]
    base_url: str | None = None
    api_key_ref: str | None = None
    key_suffix: str = ""
    context: Context = Field(default_factory=Context)
    probe: Probe = Field(default_factory=Probe)
    supports_tools: bool = False


class Appearance(Record):
    """Display preferences. Defaults come from the design mock: dark, medium, everything shown."""

    theme: Literal["dark", "light", "system"] = "dark"
    font: Literal["small", "medium", "large"] = "medium"
    show_thinking: bool = True
    keep_thinking_open: bool = True
    show_terminal: bool = True


class Settings(Record):
    locale: Literal["fa", "en"] = "fa"
    default_model: str | None = None
    default_mode: Literal["read-only", "ask", "auto"] = "ask"
    appearance: Appearance = Field(default_factory=Appearance)
    retention_days: int = Field(default=30, ge=0, le=3650)
    """Days of run history to keep. Zero keeps everything."""


class Preset(Record):
    name: str
    url: str | None


class Workspace(Record):
    path: str
    name: str
    branch: str | None = None


class TaskRecord(Record):
    waiting_on: list[Literal["approval", "question"]] = Field(default_factory=list)
    id: str
    workspace: str
    title: str
    model: str
    mode: Literal["read-only", "ask", "auto"] = "ask"
    status: Literal["running", "completed", "stopped", "error", "interrupted"] = "running"
    worktree: str | None = None
    """Where the run actually executed when the Worktree option was used."""
    schedule_id: str | None = None
    """Which schedule started this run, if any. The link the Schedule row counts from."""


class WorkspaceSelection(Record):
    path: str


class WorkspaceState(Record):
    recent: list[Workspace] = Field(default_factory=list)
    selected: str | None = None
    tasks: list[TaskRecord] = Field(default_factory=list)
