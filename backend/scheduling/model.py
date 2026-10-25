"""Schedules as data: recurrence, the permission table, and pure state transitions.

Nothing here reads the clock or the disk. A schedule's next occurrence is a function of the
schedule and a `now`, so every rule in this module is testable without waiting for time to pass.
"""

from datetime import date, datetime, time, timedelta
from typing import Literal

from pydantic import Field, field_validator, model_validator

from providers.base import Record

Mode = Literal["read-only", "ask", "auto"]
Ceiling = Literal["report", "full"]
Repeat = Literal["daily", "weekly"]
RunStatus = Literal["running", "completed", "error", "stopped", "interrupted", "missed"]

MODES: tuple[Mode, ...] = ("read-only", "ask", "auto")
"""The three modes in strictness order; an index is a rank."""

CEILINGS: tuple[Ceiling, ...] = ("report", "full")

_STRICTNESS: dict[str, int] = {"read-only": 0, "ask": 1, "auto": 2, "report": 0, "full": 2}
"""Rank of each value. `report` is as strict as read-only, `full` as permissive as auto."""


def effective_mode(mode: Mode, ceiling: Ceiling) -> Mode:
    """The stricter of the two.

    A ceiling can only ever tighten: `report` forces read-only, `full` leaves the mode alone.
    Nothing here can widen a mode, which is why the ceiling is safe to expose in a dialog.
    """
    return MODES[min(_STRICTNESS[mode], _STRICTNESS[ceiling])]


def parse_clock(value: str) -> time:
    """`HH:MM`, 24-hour. Rejects `2:00` and `02:60` rather than guessing."""
    if len(value) != 5 or value[2] != ":":
        raise ValueError("Use HH:MM")
    hours, minutes = value[:2], value[3:]
    if not (hours.isdigit() and minutes.isdigit()):
        raise ValueError("Use HH:MM")
    if int(hours) > 23 or int(minutes) > 59:
        raise ValueError("Use a real time of day")
    return time(int(hours), int(minutes))


def next_run_after(schedule: "ScheduleRecord", now: datetime) -> datetime | None:
    """The first occurrence strictly after `now`, or None once the schedule has expired.

    Strictly after matters: a tick that lands exactly on the minute must not re-fire the
    occurrence it just ran, and a run that finishes at 02:00:00 must not start again.
    """
    clock = parse_clock(schedule.time)
    candidate = datetime.combine(now.date(), clock)
    if schedule.repeat == "weekly":
        target = schedule.weekday if schedule.weekday is not None else now.weekday()
        candidate += timedelta(days=(target - now.weekday()) % 7)
        if candidate <= now:
            candidate += timedelta(days=7)
    elif candidate <= now:
        candidate += timedelta(days=1)
    if schedule.valid_until is not None and candidate.date() > schedule.valid_until:
        return None
    return candidate


def is_due(schedule: "ScheduleRecord", now: datetime) -> bool:
    return (
        schedule.enabled
        and schedule.next_run_at is not None
        and schedule.next_run_at <= now
    )


def is_overdue(schedule: "ScheduleRecord", now: datetime) -> bool:
    """Due and not yet reported. The difference decides "start it" versus "offer it"."""
    return is_due(schedule, now) and schedule.missed_at is None


def expired(schedule: "ScheduleRecord") -> bool:
    return schedule.next_run_at is None


class ScheduleRecord(Record):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    name: str = Field(min_length=1, max_length=120)
    prompt: str = Field(min_length=1, max_length=32000)
    workspace: str = Field(min_length=1)
    model: str = Field(min_length=1, max_length=64)
    mode: Mode = "read-only"
    ceiling: Ceiling = "report"
    repeat: Repeat = "daily"
    weekday: int | None = Field(default=None, ge=0, le=6)
    """Monday is 0. Required for weekly, refused for daily."""
    time: str = "02:00"
    valid_until: date | None = None
    """Inclusive last day. None is long-term."""
    enabled: bool = True
    created_at: datetime
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    last_status: RunStatus | None = None
    last_run_id: str | None = None
    missed_at: datetime | None = None
    """When the occurrence that was never started was due. Cleared by run-now or skip."""
    last_error: str | None = None

    @field_validator("name", "prompt")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Must not be blank")
        return value

    @field_validator("time")
    @classmethod
    def clock(cls, value: str) -> str:
        parse_clock(value)
        return value

    @model_validator(mode="after")
    def weekday_matches_repeat(self) -> "ScheduleRecord":
        if self.repeat == "weekly" and self.weekday is None:
            raise ValueError("A weekly schedule needs a weekday")
        if self.repeat == "daily" and self.weekday is not None:
            raise ValueError("A daily schedule has no weekday")
        return self

    @property
    def mode_effective(self) -> Mode:
        return effective_mode(self.mode, self.ceiling)


class ScheduleInput(Record):
    """What a person can set. Everything else is the engine's bookkeeping."""

    name: str = Field(min_length=1, max_length=120)
    prompt: str = Field(min_length=1, max_length=32000)
    workspace: str = Field(min_length=1)
    model: str = Field(min_length=1, max_length=64)
    mode: Mode = "read-only"
    ceiling: Ceiling = "report"
    repeat: Repeat = "daily"
    weekday: int | None = Field(default=None, ge=0, le=6)
    time: str = "02:00"
    valid_until: date | None = None
    enabled: bool = True

    @field_validator("name", "prompt")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Must not be blank")
        return value

    @field_validator("time")
    @classmethod
    def clock(cls, value: str) -> str:
        parse_clock(value)
        return value

    @model_validator(mode="after")
    def weekday_matches_repeat(self) -> "ScheduleInput":
        if self.repeat == "weekly" and self.weekday is None:
            raise ValueError("A weekly schedule needs a weekday")
        if self.repeat == "daily" and self.weekday is not None:
            raise ValueError("A daily schedule has no weekday")
        return self


class ScheduleList(Record):
    schedules: list[ScheduleRecord] = Field(default_factory=list)
    pending: dict[str, int] = Field(default_factory=dict)
    """Pending approvals per schedule id. Computed from the inbox, never stored."""
    now: datetime
    """The engine's clock, so the client does not have to trust its own."""


class ScheduleToggle(Record):
    enabled: bool


def started(schedule: ScheduleRecord, at: datetime, run_id: str) -> ScheduleRecord:
    """A run began. The next occurrence is computed from `at`, never from the old one."""
    return schedule.model_copy(
        update={
            "next_run_at": next_run_after(schedule, at),
            "last_run_at": at,
            "last_run_id": run_id,
            "last_status": "running",
            "missed_at": None,
            "last_error": None,
        }
    )


def finished(schedule: ScheduleRecord, status: RunStatus) -> ScheduleRecord:
    return schedule.model_copy(update={"last_status": status})


def marked_missed(schedule: ScheduleRecord, now: datetime) -> ScheduleRecord:
    """The occurrence was due while the app was closed: remember it, advance past it."""
    return schedule.model_copy(
        update={
            "missed_at": schedule.next_run_at or now,
            "next_run_at": next_run_after(schedule, now),
            "last_status": "missed",
        }
    )


def skipped(schedule: ScheduleRecord, now: datetime) -> ScheduleRecord:
    return schedule.model_copy(
        update={"missed_at": None, "next_run_at": next_run_after(schedule, now)}
    )


def failed(schedule: ScheduleRecord, message: str, now: datetime) -> ScheduleRecord:
    """Record why this occurrence could not start.

    The occurrence is *not* advanced past: a missing model or a locked folder is usually fixed
    within the hour, and skipping to tomorrow would quietly lose tonight's run. The ticker
    holds the backoff, so this stays a pure record of the last attempt.
    """
    del now  # the transition itself does not depend on the clock
    return schedule.model_copy(update={"last_error": message, "last_status": "error"})


def reloaded(schedule: ScheduleRecord, now: datetime) -> ScheduleRecord:
    """After a restart: fill in a missing occurrence and stop claiming a run is still going.

    An occurrence that fell due while the app was closed is *kept*, not recomputed: the
    ticker's startup pass has to see it to offer "run now". Recomputing from `now` here would
    quietly delete the one thing a missed run is.
    """
    status = schedule.last_status
    next_at = schedule.next_run_at
    if next_at is None:
        next_at = next_run_after(schedule, now)
    return schedule.model_copy(
        update={
            "next_run_at": next_at,
            "last_status": "interrupted" if status == "running" else status,
        }
    )
