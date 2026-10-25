"""Schedules persist in app data, survive a restart, and never touch the workspace."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from scheduling.model import ScheduleInput, is_due
from store.catalog import Catalog
from store.schedules import (
    add_schedule,
    delete_schedule,
    find_schedule,
    list_schedules,
    save_schedule,
    set_enabled,
    update_schedule,
)

NOW = datetime(2026, 10, 21, 12, 0)


def value(**overrides: object) -> ScheduleInput:
    fields: dict[str, object] = {
        "name": "Nightly tests",
        "prompt": "Run the tests and report failures",
        "workspace": "C:/work/invoice-parser",
        "model": "demo",
        "time": "02:00",
    }
    fields.update(overrides)
    return ScheduleInput.model_validate(fields)


def test_survives_restart(tmp_path: Path) -> None:
    path = tmp_path / "catalog.json"
    catalog = Catalog(path)
    created = add_schedule(catalog, value(), NOW)
    assert created.next_run_at == datetime(2026, 10, 22, 2, 0)

    restored = Catalog(path)
    schedules = list_schedules(restored)
    assert len(schedules) == 1
    again = schedules[0]
    assert again.id == created.id
    assert again.name == created.name
    assert again.prompt == created.prompt
    assert again.workspace == created.workspace
    assert (again.mode, again.ceiling) == ("read-only", "report")
    assert again.enabled is True
    assert again.next_run_at == created.next_run_at


def test_an_overdue_occurrence_survives_a_restart(tmp_path: Path) -> None:
    """The whole point of a missed run: closing the app must not erase what was due."""
    path = tmp_path / "catalog.json"
    catalog = Catalog(path)
    created = add_schedule(catalog, value(), NOW)
    due = datetime(2026, 10, 22, 2, 0)
    assert created.next_run_at == due
    catalog.data.schedules[0].next_run_at = due
    catalog.persist()

    restored = Catalog(path)
    kept = list_schedules(restored)[0]
    assert kept.next_run_at == due
    # A day later it is due and not yet reported: the startup pass has to offer it.
    assert is_due(kept, due + timedelta(days=1))


def test_a_running_status_becomes_interrupted(tmp_path: Path) -> None:
    path = tmp_path / "catalog.json"
    catalog = Catalog(path)
    created = add_schedule(catalog, value(), NOW)
    save_schedule(catalog, created.model_copy(update={"last_status": "running"}))
    restored = Catalog(path)
    assert list_schedules(restored)[0].last_status == "interrupted"


def test_schedule_never_written_to_the_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    (workspace / ".harness").mkdir(parents=True)
    (workspace / ".harness" / "rules.json").write_text("{}", encoding="utf-8")
    catalog = Catalog(tmp_path / "catalog.json")
    created = add_schedule(
        catalog, value(workspace=str(workspace), name="canary-name-4821"), NOW
    )
    assert created.id
    written = [
        item
        for item in workspace.rglob("*")
        if item.is_file() and "canary-name-4821" in item.read_text(encoding="utf-8")
    ]
    assert written == []
    assert "canary-name-4821" in (tmp_path / "catalog.json").read_text(encoding="utf-8")


def test_old_catalog_loads_with_no_schedules(tmp_path: Path) -> None:
    """A catalog written before this phase has no `schedules` key at all."""
    path = tmp_path / "catalog.json"
    path.write_text(
        '{"key_digests":{},"models":{},"settings":{},"workspaces":{"recent":[],"tasks":[]}}',
        encoding="utf-8",
    )
    catalog = Catalog(path)
    assert list_schedules(catalog) == []


def test_edit_reschedules_and_keeps_history(tmp_path: Path) -> None:
    catalog = Catalog(tmp_path / "catalog.json")
    created = add_schedule(catalog, value(), NOW)
    ran = save_schedule(
        catalog,
        created.model_copy(update={"last_status": "completed", "last_run_id": "run-1"}),
    )
    assert ran.last_run_id == "run-1"

    edited = update_schedule(
        catalog, created.id, value(name="Weekly", repeat="weekly", weekday=4, time="09:00"), NOW
    )
    assert edited.id == created.id
    assert edited.name == "Weekly"
    assert edited.created_at == created.created_at
    assert edited.last_run_id == "run-1"
    assert edited.last_status == "completed"
    # A weekly Friday 09:00 created on Wednesday runs this Friday.
    assert edited.next_run_at == datetime(2026, 10, 23, 9, 0)
    assert len(list_schedules(catalog)) == 1


def test_an_expired_validity_is_refused(tmp_path: Path) -> None:
    catalog = Catalog(tmp_path / "catalog.json")
    with pytest.raises(ValueError, match="already ended"):
        add_schedule(catalog, value(valid_until=(NOW.date() - timedelta(days=1))), NOW)
    assert list_schedules(catalog) == []


def test_the_switch_reschedules_from_now(tmp_path: Path) -> None:
    catalog = Catalog(tmp_path / "catalog.json")
    created = add_schedule(catalog, value(), NOW)
    off = set_enabled(catalog, created.id, False, NOW + timedelta(days=2))
    assert off.enabled is False
    assert off.missed_at is None
    # R11: pausing keeps the occurrence it already had, so the paused row can still say when
    # it would have run and nothing is rewritten behind the person's back.
    assert off.next_run_at == created.next_run_at
    on = set_enabled(catalog, created.id, True, NOW + timedelta(days=2))
    assert on.enabled is True
    # Resuming is not a backlog: the next occurrence is the first one after "now".
    assert on.next_run_at == datetime(2026, 10, 24, 2, 0)


def test_delete_and_missing_ids(tmp_path: Path) -> None:
    catalog = Catalog(tmp_path / "catalog.json")
    created = add_schedule(catalog, value(), NOW)
    assert find_schedule(catalog, created.id) is not None
    assert find_schedule(catalog, "nope") is None
    with pytest.raises(KeyError):
        update_schedule(catalog, "nope", value(), NOW)
    with pytest.raises(KeyError):
        set_enabled(catalog, "nope", False, NOW)
    assert delete_schedule(catalog, created.id) is True
    assert delete_schedule(catalog, created.id) is False
    assert list_schedules(catalog) == []
