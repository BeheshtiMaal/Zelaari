"""Bounded planning wire contracts; acceptance is always an engine decision."""

from datetime import datetime
from pathlib import PurePosixPath
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

Identity = Annotated[str, StringConstraints(pattern=r"^[a-zA-Z0-9_-]{1,64}$")]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)]
StepStatus = Literal["pending", "in_progress", "completed", "failed"]


class PlanningModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlanStep(PlanningModel):
    id: Identity
    title: Title
    expected_files: list[Annotated[str, Field(min_length=1, max_length=512)]] = Field(
        default_factory=list, max_length=64
    )
    verify_command: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
        | None
    ) = None
    high_risk: bool = Field(default=False, strict=True)

    @field_validator("expected_files")
    @classmethod
    def safe_patterns(cls, values: list[str]) -> list[str]:
        for value in values:
            # No drive/ADS, host paths, traversal, control chars or ambiguous separators.
            if (
                value.startswith("/")
                or "\\" in value
                or ":" in value
                or any(ord(char) < 32 for char in value)
                or ".." in value.split("/")
                or value.strip() != value
                or str(PurePosixPath(value)) in {".", ""}
            ):
                raise ValueError("Expected files must be workspace-relative POSIX patterns")
        return list(dict.fromkeys(values))


class PlanSubmission(PlanningModel):
    steps: list[PlanStep] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def unique_ids(self) -> Self:
        if len({step.id for step in self.steps}) != len(self.steps):
            raise ValueError("Plan step IDs must be unique")
        return self


class PlanningSettings(PlanningModel):
    step_threshold: int = Field(default=4, ge=1, le=64, strict=True)
    file_threshold: int = Field(default=3, ge=1, le=10000, strict=True)
    deviation_gate: bool = Field(default=True, strict=True)


class FileScope(PlanningModel):
    known_files: list[str] = Field(default_factory=list, max_length=10000)
    uncertain: bool = False
    revision: str = Field(pattern=r"^[a-f0-9]{64}$")


class StepProgress(PlanningModel):
    step_id: Identity
    status: StepStatus = "pending"
    started_at: datetime | None = None
    ended_at: datetime | None = None


class PlanRecord(PlanningModel):
    run_id: Identity
    plan_id: Identity
    revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    baseline_ids: list[Identity] = Field(min_length=1, max_length=64)
    submission: PlanSubmission
    progress: list[StepProgress] = Field(min_length=1, max_length=64)
    adoption: Literal["pending", "automatic", "approved", "rejected"]
    gate_reasons: list[str] = Field(default_factory=list, max_length=16)
    file_scope: FileScope
    settings: PlanningSettings

    @model_validator(mode="after")
    def consistent_progress(self) -> Self:
        if [item.step_id for item in self.progress] != [step.id for step in self.submission.steps]:
            raise ValueError("Progress must match accepted ordered step IDs")
        if len(set(self.baseline_ids)) != len(self.baseline_ids):
            raise ValueError("Baseline step IDs must be unique")
        if sum(item.status == "in_progress" for item in self.progress) > 1:
            raise ValueError("Only one parent step can be active")
        return self


class ActivityScope(PlanningModel):
    scope_id: Identity
    step_id: Identity | None = None
    parent_scope_id: Identity | None = None
    turn_id: Identity | None = None
    agent: Literal["parent", "reviewer", "researcher"] = "parent"
    model: str | None = None


class SteeringSubmission(PlanningModel):
    submission_id: Identity
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32000)]


class SteeringRecord(SteeringSubmission):
    run_id: Identity
    ordinal: int = Field(ge=1)
    status: Literal["queued", "delivered", "cancelled"] = "queued"
    queued_at: datetime
    delivered_at: datetime | None = None
