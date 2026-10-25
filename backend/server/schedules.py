"""Schedule routes.

Creating a schedule is the person's own action on their own app, so it is not an inbox
approval (D39). The one dangerous value — full access — is a visible choice in the dialog and
is capped again by the permission middleware when the run actually happens.
"""

from collections.abc import Awaitable, Callable

from fastapi import APIRouter, HTTPException

from agent.events import RunResponse
from scheduling.model import (
    ScheduleInput,
    ScheduleList,
    ScheduleRecord,
    ScheduleToggle,
)
from scheduling.ticker import Scheduler
from store.catalog import Catalog
from store.schedules import (
    add_schedule,
    delete_schedule,
    list_schedules,
    set_enabled,
    update_schedule,
)
from tools.jail import JailError, workspace_root

PendingCounts = Callable[[], Awaitable[dict[str, int]]]


def schedules_routes(
    catalog: Catalog, scheduler: Scheduler, pending: PendingCounts
) -> APIRouter:
    router = APIRouter()

    def accessible(path: str) -> None:
        try:
            workspace_root(path)
        except (JailError, ValueError, OSError):
            raise HTTPException(400, "Choose an accessible workspace") from None

    @router.get("/schedules")
    async def all_schedules() -> ScheduleList:
        return ScheduleList(
            schedules=list_schedules(catalog),
            pending=await pending(),
            now=scheduler.clock(),
        )

    @router.post("/schedules", status_code=201)
    def create(value: ScheduleInput) -> ScheduleRecord:
        accessible(value.workspace)
        try:
            return add_schedule(catalog, value, scheduler.clock())
        except ValueError as error:
            raise HTTPException(400, str(error)) from None

    @router.put("/schedules/{schedule_id}")
    def update(schedule_id: str, value: ScheduleInput) -> ScheduleRecord:
        accessible(value.workspace)
        try:
            return update_schedule(catalog, schedule_id, value, scheduler.clock())
        except KeyError:
            raise HTTPException(404, "Unknown schedule") from None
        except ValueError as error:
            raise HTTPException(400, str(error)) from None

    @router.delete("/schedules/{schedule_id}")
    def remove(schedule_id: str) -> dict[str, bool]:
        if not delete_schedule(catalog, schedule_id):
            raise HTTPException(404, "Unknown schedule")
        return {"deleted": True}

    @router.post("/schedules/{schedule_id}/enabled")
    def toggle(schedule_id: str, value: ScheduleToggle) -> ScheduleRecord:
        try:
            return set_enabled(catalog, schedule_id, value.enabled, scheduler.clock())
        except KeyError:
            raise HTTPException(404, "Unknown schedule") from None

    @router.post("/schedules/{schedule_id}/run", status_code=202)
    async def run_now(schedule_id: str) -> RunResponse:
        try:
            return RunResponse(run_id=await scheduler.run_now(schedule_id))
        except KeyError:
            raise HTTPException(404, "Unknown schedule") from None
        except (ValueError, OSError) as error:
            raise HTTPException(409, str(error) or "The run could not start") from None

    @router.post("/schedules/{schedule_id}/skip")
    def skip(schedule_id: str) -> ScheduleRecord:
        try:
            return scheduler.skip(schedule_id)
        except KeyError:
            raise HTTPException(404, "Unknown schedule") from None

    return router
