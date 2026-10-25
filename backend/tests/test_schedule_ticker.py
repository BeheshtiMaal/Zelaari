"""The ticker turns a due schedule into a real run, and offers the ones it could not watch."""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from agent.events import RunRequest
from scheduling.model import ScheduleInput, ScheduleRecord
from scheduling.ticker import GRACE, RETRY, Scheduler, decide
from store.catalog import Catalog
from store.schedules import add_schedule, find_schedule, save_schedule

NOW = datetime(2026, 10, 21, 12, 0)
DUE = datetime(2026, 10, 21, 2, 0)


class Clock:
    """A clock a test can move."""

    def __init__(self, at: datetime) -> None:
        self.at = at

    def __call__(self) -> datetime:
        return self.at


class Recorder:
    """Stands in for RunManager.start: records what it was asked, returns an id."""

    def __init__(self) -> None:
        self.requests: list[RunRequest] = []

    async def __call__(self, request: RunRequest) -> str:
        self.requests.append(request)
        return f"run-{len(self.requests)}"


def workspace(tmp_path: Path) -> str:
    root = tmp_path / "ws"
    (root / ".harness").mkdir(parents=True, exist_ok=True)
    return str(root)


def seed(
    catalog: Catalog,
    path: str,
    *,
    next_run_at: datetime | None = DUE,
    **overrides: object,
) -> ScheduleRecord:
    fields: dict[str, object] = {
        "name": "Nightly tests",
        "prompt": "Run the tests",
        "workspace": path,
        "model": "demo",
        "time": "02:00",
    }
    fields.update(overrides)
    created = add_schedule(catalog, ScheduleInput.model_validate(fields), NOW)
    return save_schedule(catalog, created.model_copy(update={"next_run_at": next_run_at}))


def engine_for(
    catalog: Catalog, recorder: Recorder, at: datetime = NOW
) -> tuple[Scheduler, Clock]:
    clock = Clock(at)
    return Scheduler(catalog, recorder, clock=clock), clock


class TestOffering:
    def test_overdue_becomes_missed_and_starts_nothing(self, tmp_path: Path) -> None:
        catalog, recorder = Catalog(tmp_path / "catalog.json"), Recorder()
        seeded = seed(catalog, workspace(tmp_path))
        engine, _ = engine_for(catalog, recorder)
        assert asyncio.run(engine.tick()) == []
        assert recorder.requests == []
        after = find_schedule(catalog, seeded.id)
        assert after is not None
        assert after.missed_at == DUE
        assert after.next_run_at == datetime(2026, 10, 22, 2, 0)
        assert after.last_status == "missed"

    def test_a_slightly_late_occurrence_is_started_not_offered(self, tmp_path: Path) -> None:
        catalog, recorder = Catalog(tmp_path / "catalog.json"), Recorder()
        seeded = seed(catalog, workspace(tmp_path))
        engine, _ = engine_for(catalog, recorder, DUE + timedelta(minutes=1))
        assert asyncio.run(engine.tick()) == [seeded.id]
        assert len(recorder.requests) == 1

    def test_the_grace_window_is_the_boundary(self) -> None:
        record = bare_record()
        assert decide(record, DUE + GRACE) == "start"
        assert decide(record, DUE + GRACE + timedelta(seconds=1)) == "offer"

    def test_run_now_starts_one_run_and_clears_missed(self, tmp_path: Path) -> None:
        catalog, recorder = Catalog(tmp_path / "catalog.json"), Recorder()
        seeded = seed(catalog, workspace(tmp_path))
        engine, _ = engine_for(catalog, recorder)
        asyncio.run(engine.tick())
        missed = find_schedule(catalog, seeded.id)
        assert missed is not None and missed.missed_at == DUE

        assert asyncio.run(engine.run_now(seeded.id)) == "run-1"
        assert len(recorder.requests) == 1
        after = find_schedule(catalog, seeded.id)
        assert after is not None
        assert after.missed_at is None
        assert after.last_run_id == "run-1"
        assert after.last_status == "running"
        # The next tick does not start a second run for the same occurrence.
        assert asyncio.run(engine.tick()) == []

    def test_skip_starts_nothing(self, tmp_path: Path) -> None:
        catalog, recorder = Catalog(tmp_path / "catalog.json"), Recorder()
        seeded = seed(catalog, workspace(tmp_path))
        engine, _ = engine_for(catalog, recorder)
        asyncio.run(engine.tick())
        engine.skip(seeded.id)
        after = find_schedule(catalog, seeded.id)
        assert after is not None
        assert after.missed_at is None
        assert after.next_run_at == datetime(2026, 10, 22, 2, 0)
        assert recorder.requests == []


class TestStarting:
    def test_next_run_advances_from_now(self, tmp_path: Path) -> None:
        catalog, recorder = Catalog(tmp_path / "catalog.json"), Recorder()
        seeded = seed(catalog, workspace(tmp_path))
        engine, _ = engine_for(catalog, recorder, DUE + timedelta(seconds=30))
        asyncio.run(engine.tick())
        after = find_schedule(catalog, seeded.id)
        assert after is not None
        assert after.next_run_at == datetime(2026, 10, 22, 2, 0)
        assert after.last_status == "running"

    def test_the_run_carries_the_effective_mode(self, tmp_path: Path) -> None:
        catalog, recorder = Catalog(tmp_path / "catalog.json"), Recorder()
        seeded = seed(catalog, workspace(tmp_path), mode="auto", ceiling="report")
        engine, _ = engine_for(catalog, recorder, DUE + timedelta(minutes=1))
        asyncio.run(engine.tick())
        assert recorder.requests[0].mode == "read-only"
        assert recorder.requests[0].schedule_id == seeded.id

    def test_full_access_keeps_the_mode_it_was_given(self, tmp_path: Path) -> None:
        catalog, recorder = Catalog(tmp_path / "catalog.json"), Recorder()
        seed(catalog, workspace(tmp_path), mode="auto", ceiling="full")
        engine, _ = engine_for(catalog, recorder, DUE + timedelta(minutes=1))
        asyncio.run(engine.tick())
        assert recorder.requests[0].mode == "auto"

    def test_two_due_schedules_both_start(self, tmp_path: Path) -> None:
        catalog, recorder = Catalog(tmp_path / "catalog.json"), Recorder()
        path = workspace(tmp_path)
        seed(catalog, path, name="First")
        seed(catalog, path, name="Second")
        engine, _ = engine_for(catalog, recorder, DUE + timedelta(minutes=1))
        assert len(asyncio.run(engine.tick())) == 2
        assert len(recorder.requests) == 2

    def test_a_disabled_schedule_never_starts(self, tmp_path: Path) -> None:
        catalog, recorder = Catalog(tmp_path / "catalog.json"), Recorder()
        seeded = seed(catalog, workspace(tmp_path), enabled=False)
        engine, _ = engine_for(catalog, recorder)
        assert asyncio.run(engine.tick()) == []
        assert recorder.requests == []
        after = find_schedule(catalog, seeded.id)
        assert after is not None and after.next_run_at == DUE

    def test_expired_never_starts(self, tmp_path: Path) -> None:
        catalog, recorder = Catalog(tmp_path / "catalog.json"), Recorder()
        seed(catalog, workspace(tmp_path), next_run_at=None)
        engine, _ = engine_for(catalog, recorder)
        assert asyncio.run(engine.tick()) == []
        assert recorder.requests == []


class TestFailures:
    def test_missing_model_is_reported(self, tmp_path: Path) -> None:
        catalog, recorder = Catalog(tmp_path / "catalog.json"), Recorder()
        seeded = seed(catalog, workspace(tmp_path), model="not-configured")
        engine, _ = engine_for(catalog, recorder, DUE + timedelta(minutes=1))
        assert asyncio.run(engine.tick()) == []
        assert recorder.requests == []
        after = find_schedule(catalog, seeded.id)
        assert after is not None
        assert after.last_error == "The model is not available"
        assert after.last_status == "error"
        # The occurrence is not thrown away: tonight's run is not lost to a bad model id.
        assert after.next_run_at == DUE

    def test_a_failure_backs_off_then_recovers(self, tmp_path: Path) -> None:
        catalog, recorder = Catalog(tmp_path / "catalog.json"), Recorder()
        seeded = seed(catalog, workspace(tmp_path), model="not-configured")
        engine, clock = engine_for(catalog, recorder, DUE + timedelta(minutes=1))
        asyncio.run(engine.tick())
        assert recorder.requests == []

        # Inside the backoff window nothing is attempted at all.
        clock.at = DUE + timedelta(minutes=1) + RETRY - timedelta(seconds=1)
        assert asyncio.run(engine.tick()) == []
        assert recorder.requests == []

        # The person fixes the model; the first attempt after the window starts the run.
        fixed = find_schedule(catalog, seeded.id)
        assert fixed is not None
        save_schedule(catalog, fixed.model_copy(update={"model": "demo"}))
        clock.at = DUE + timedelta(minutes=1) + RETRY + timedelta(seconds=1)
        assert asyncio.run(engine.tick()) == [seeded.id]
        assert len(recorder.requests) == 1
        recovered = find_schedule(catalog, seeded.id)
        assert recovered is not None
        assert recovered.last_error is None
        assert recovered.last_status == "running"

    def test_moved_workspace_is_reported(self, tmp_path: Path) -> None:
        catalog, recorder = Catalog(tmp_path / "catalog.json"), Recorder()
        seeded = seed(catalog, str(tmp_path / "gone"))
        engine, _ = engine_for(catalog, recorder, DUE + timedelta(minutes=1))
        assert asyncio.run(engine.tick()) == []
        after = find_schedule(catalog, seeded.id)
        assert after is not None
        assert after.last_error == "The workspace is not accessible"
        assert recorder.requests == []

    def test_run_now_reports_the_same_reason(self, tmp_path: Path) -> None:
        catalog, recorder = Catalog(tmp_path / "catalog.json"), Recorder()
        seeded = seed(catalog, str(tmp_path / "gone"))
        engine, _ = engine_for(catalog, recorder)
        with pytest.raises(ValueError, match="not accessible"):
            asyncio.run(engine.run_now(seeded.id))
        assert recorder.requests == []


def bare_record() -> ScheduleRecord:
    """A record built without a catalog, for the pure decision tests."""
    return ScheduleRecord(
        id="s1",
        name="Nightly",
        prompt="Run the tests",
        workspace="C:/work/app",
        model="demo",
        time="02:00",
        created_at=NOW,
        next_run_at=DUE,
    )
