"""App-data contracts for the Data and About sections. Leaf module: no engine imports."""

from pydantic import BaseModel, ConfigDict, Field


class AppDataModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WorkspaceData(AppDataModel):
    path: str
    name: str
    harness: str
    runs: int = 0
    run_bytes: int = 0
    checkpoints_bytes: int = 0
    tasks: int = 0


class DataSummary(AppDataModel):
    """What is on this device. Every number is a count, never a path inside a run."""

    app_data: str
    retention_days: int = 30
    keys: int = 0
    workspaces: list[WorkspaceData] = Field(default_factory=list)


class DeletedRuns(AppDataModel):
    workspace: str
    runs: int = 0
    bytes: int = 0
    tasks: int = 0


class AppInfo(AppDataModel):
    name: str = "CodeHarness"
    version: str
    licence: str = "MIT"
    app_data: str
    log_directory: str
