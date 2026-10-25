"""The ticker: the only thing that turns a due schedule into a run.

It lives in the engine process, so it stops when the app stops. That is the product rule
("runs only while the app is open"), not an implementation accident — there is no service to
install and nothing that can act on a machine nobody is sitting at.
"""

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import datetime, timedelta
from typing import Literal, cast

from agent.events import Event, RunRequest
from scheduling.model import (
    RunStatus,
    ScheduleRecord,
    failed,
    finished,
    is_due,
    marked_missed,
    skipped,
    started,
)
from store.catalog import Catalog
from store.schedules import find_schedule, list_schedules, save_schedule
from tools.jail import JailError, workspace_root

INTERVAL = 20.0
"""How often the ticker looks. A schedule is minute-resolution, so this is plenty."""
GRACE = timedelta(minutes=5)
"""How late an occurrence may be and still be started.

Past this the app cannot claim it was watching — the machine slept, or the app was closed —
so the occurrence is offered instead of started.
"""
RETRY = timedelta(minutes=5)
"""How long to wait before trying a schedule that just failed."""

Decision = Literal["start", "offer", "wait"]
Starter = Callable[[RunRequest], Awaitable[str]]
Watcher = Callable[[str], AsyncIterator[Event]]
"""Follows a run's own event stream so the row can say how it ended."""

log = logging.getLogger("codeharness.schedule")


def decide(
    schedule: ScheduleRecord, now: datetime, retry_at: datetime | None = None
) -> Decision:
    """What to do with one schedule at this moment. Pure, so the timing rules are testable.

    `retry_at` is the ticker's backoff after a failed attempt; it is memory, not data,
    because a restart should try again immediately rather than inherit a stale wait.
    """
    if not schedule.enabled or schedule.next_run_at is None:
        return "wait"
    if schedule.missed_at is not None:
        # Already offered and waiting for the person to choose.
        return "wait"
    if not is_due(schedule, now):
        return "wait"
    if retry_at is not None and now < retry_at:
        return "wait"
    if schedule.last_error is None and now - schedule.next_run_at > GRACE:
        return "offer"
    return "start"


class Scheduler:
    def __init__(
        self,
        catalog: Catalog,
        start: Starter,
        *,
        clock: Callable[[], datetime] | None = None,
        interval: float = INTERVAL,
        events: Watcher | None = None,
    ) -> None:
        self.catalog = catalog
        self.start_run = start
        self.clock = clock or datetime.now
        self.interval = interval
        self.events = events
        self._retry: dict[str, datetime] = {}
        self._task: asyncio.Task[None] | None = None
        self._watchers: set[asyncio.Task[None]] = set()

    # -- one pass ----------------------------------------------------------------
    async def tick(self) -> list[str]:
        """Look at every schedule once. Returns the ids it started, so a test can assert it."""
        now = self.clock()
        began: list[str] = []
        for schedule in list_schedules(self.catalog):
            action = decide(schedule, now, self._retry.get(schedule.id))
            if action == "offer":
                save_schedule(self.catalog, marked_missed(schedule, now))
                continue
            if action != "start":
                continue
            run_id = await self._attempt(schedule, now)
            if run_id is not None:
                began.append(schedule.id)
        return began

    async def _attempt(self, schedule: ScheduleRecord, now: datetime) -> str | None:
        problem = self.problem(schedule)
        if problem is not None:
            save_schedule(self.catalog, failed(schedule, problem, now))
            self._retry[schedule.id] = now + RETRY
            return None
        request = RunRequest(
            task=schedule.prompt,
            workspace=schedule.workspace,
            model=schedule.model,
            mode=schedule.mode_effective,
            schedule_id=schedule.id,
        )
        try:
            run_id = await self.start_run(request)
        except (ValueError, OSError, RuntimeError) as error:
            save_schedule(self.catalog, failed(schedule, str(error) or "The run failed", now))
            self._retry[schedule.id] = now + RETRY
            return None
        self._began(schedule, now, run_id)
        return run_id

    def _began(self, schedule: ScheduleRecord, now: datetime, run_id: str) -> None:
        save_schedule(self.catalog, started(schedule, now, run_id))
        self._retry.pop(schedule.id, None)
        if self.events is None:
            return
        watcher = asyncio.create_task(self._watch(schedule.id, run_id))
        self._watchers.add(watcher)
        watcher.add_done_callback(self._watchers.discard)

    async def _watch(self, schedule_id: str, run_id: str) -> None:
        """Follow the run so the row reports how it ended, not only that it started.

        The stream ends at `run.finished` (the bus closes it), so this task cannot outlive
        the run it is watching.
        """
        if self.events is None:
            return
        try:
            async for event in self.events(run_id):
                if event.type != "run.finished":
                    continue
                schedule = find_schedule(self.catalog, schedule_id)
                if schedule is not None:
                    status = cast(str, getattr(event, "status", "completed"))
                    if status not in {"completed", "error", "stopped"}:
                        status = "completed"
                    save_schedule(self.catalog, finished(schedule, cast(RunStatus, status)))
                return
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - a watcher must never take the ticker down
            log.exception("schedule watcher failed")

    def problem(self, schedule: ScheduleRecord) -> str | None:
        """Why this schedule cannot run right now, or None. Cheap checks only."""
        try:
            self.catalog.require(schedule.model)
        except ValueError:
            return "The model is not available"
        try:
            workspace_root(schedule.workspace)
        except (JailError, ValueError, OSError):
            return "The workspace is not accessible"
        return None

    # -- person-initiated --------------------------------------------------------
    async def run_now(self, schedule_id: str) -> str:
        """Start one run for this schedule, whatever its recurrence says.

        This is the answer to "run now" and the retry after a fixed model: it does not wait
        for the next occurrence, and it does not need the schedule to be enabled.
        """
        schedule = find_schedule(self.catalog, schedule_id)
        if schedule is None:
            raise KeyError(schedule_id)
        now = self.clock()
        problem = self.problem(schedule)
        if problem is not None:
            save_schedule(self.catalog, failed(schedule, problem, now))
            raise ValueError(problem)
        run_id = await self.start_run(
            RunRequest(
                task=schedule.prompt,
                workspace=schedule.workspace,
                model=schedule.model,
                mode=schedule.mode_effective,
                schedule_id=schedule.id,
            )
        )
        self._began(schedule, now, run_id)
        return run_id

    def skip(self, schedule_id: str) -> ScheduleRecord:
        """Dismiss a missed occurrence without running it."""
        schedule = find_schedule(self.catalog, schedule_id)
        if schedule is None:
            raise KeyError(schedule_id)
        return save_schedule(self.catalog, skipped(schedule, self.clock()))

    # -- lifecycle ---------------------------------------------------------------
    def begin(self) -> None:
        """Start the loop. Called from the app lifespan, never at import time."""
        if self._task is None:
            self._task = asyncio.create_task(self._loop())

    async def _loop(self) -> None:
        while True:
            try:
                await self.tick()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 - a dead ticker would stop every schedule silently
                log.exception("schedule tick failed")
            await asyncio.sleep(self.interval)

    async def close(self) -> None:
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        watchers, self._watchers = self._watchers, set()
        for watcher in watchers:
            watcher.cancel()
        if watchers:
            await asyncio.gather(*watchers, return_exceptions=True)
