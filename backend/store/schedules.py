"""Schedules in the app-data catalog: one lock, one atomic write, one place to look.

Every time in this module is naive local wall clock, because recurrence is "02:00 on this
machine". Converting to UTC and back would make a schedule move when the machine changes zone.
"""

from datetime import datetime
from uuid import uuid4

from scheduling.model import ScheduleInput, ScheduleRecord, next_run_after
from store.catalog import Catalog


def list_schedules(catalog: Catalog) -> list[ScheduleRecord]:
    with catalog.lock:
        return [item.model_copy(deep=True) for item in catalog.data.schedules]


def find_schedule(catalog: Catalog, schedule_id: str) -> ScheduleRecord | None:
    with catalog.lock:
        found = next((item for item in catalog.data.schedules if item.id == schedule_id), None)
        return found.model_copy(deep=True) if found else None


def schedule_of(catalog: Catalog, schedule_id: str | None) -> ScheduleRecord | None:
    """The schedule behind a run, for labelling an approval. Cheap enough for every card."""
    if schedule_id is None:
        return None
    with catalog.lock:
        return next((item for item in catalog.data.schedules if item.id == schedule_id), None)


def build(value: ScheduleInput, now: datetime, schedule_id: str) -> ScheduleRecord:
    """A record with its first occurrence computed. No I/O."""
    draft = ScheduleRecord(id=schedule_id, **value.model_dump(), created_at=now)
    return draft.model_copy(update={"next_run_at": next_run_after(draft, now)})


def add_schedule(catalog: Catalog, value: ScheduleInput, now: datetime) -> ScheduleRecord:
    record = build(value, now, uuid4().hex)
    if record.next_run_at is None:
        # Every occurrence is already behind the validity date: creating it would put a row
        # on the screen that can never run.
        raise ValueError("That validity has already ended")
    with catalog.lock:
        catalog.data.schedules.append(record)
        catalog.persist()
    return record


def update_schedule(
    catalog: Catalog, schedule_id: str, value: ScheduleInput, now: datetime
) -> ScheduleRecord:
    with catalog.lock:
        old = next((item for item in catalog.data.schedules if item.id == schedule_id), None)
        if old is None:
            raise KeyError(schedule_id)
        record = build(value, now, schedule_id)
        if record.next_run_at is None:
            raise ValueError("That validity has already ended")
        # An edit reschedules, so a pending "this was missed" offer no longer applies. The
        # history of what it already ran is kept.
        record = record.model_copy(
            update={
                "created_at": old.created_at,
                "last_run_at": old.last_run_at,
                "last_status": old.last_status,
                "last_run_id": old.last_run_id,
            }
        )
        catalog.data.schedules = [
            record if item.id == schedule_id else item for item in catalog.data.schedules
        ]
        catalog.persist()
    return record


def save_schedule(catalog: Catalog, record: ScheduleRecord) -> ScheduleRecord:
    """Write back a record the ticker changed. The caller owns the transition."""
    with catalog.lock:
        catalog.data.schedules = [
            record if item.id == record.id else item for item in catalog.data.schedules
        ]
        catalog.persist()
    return record


def delete_schedule(catalog: Catalog, schedule_id: str) -> bool:
    with catalog.lock:
        before = len(catalog.data.schedules)
        catalog.data.schedules = [
            item for item in catalog.data.schedules if item.id != schedule_id
        ]
        removed = len(catalog.data.schedules) != before
        if removed:
            catalog.persist()
        return removed


def set_enabled(
    catalog: Catalog, schedule_id: str, enabled: bool, now: datetime
) -> ScheduleRecord:
    """The switch. Turning it back on reschedules from now rather than firing a backlog."""
    with catalog.lock:
        old = next((item for item in catalog.data.schedules if item.id == schedule_id), None)
        if old is None:
            raise KeyError(schedule_id)
        record = old.model_copy(
            update={
                "enabled": enabled,
                "next_run_at": next_run_after(old, now),
                "missed_at": None,
            }
        )
        catalog.data.schedules = [
            record if item.id == schedule_id else item for item in catalog.data.schedules
        ]
        catalog.persist()
    return record
