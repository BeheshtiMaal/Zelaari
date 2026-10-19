from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.sse import EventSourceResponse, ServerSentEvent

from agent.events import Event
from providers.base import WorkspaceSelection, WorkspaceState
from store.catalog import Catalog
from store.workspaces import select_workspace, task_events, workspace_state


def workspace_routes(catalog: Catalog) -> APIRouter:
    router = APIRouter()

    @router.get("/workspaces")
    def workspaces() -> WorkspaceState:
        return workspace_state(catalog)

    @router.post("/workspaces")
    def select(value: WorkspaceSelection) -> WorkspaceState:
        try:
            return select_workspace(catalog, value.path)
        except (ValueError, OSError, RuntimeError):
            raise HTTPException(
                400, "Choose an accessible project folder, not a root or home"
            ) from None

    def history(identifier: str) -> list[Event]:
        try:
            return task_events(catalog, identifier)
        except (ValueError, OSError, RuntimeError):
            raise HTTPException(404, "Task history unavailable") from None

    @router.get("/tasks/{identifier}/events", response_class=EventSourceResponse)
    async def replay(
        events: Annotated[list[Event], Depends(history)],
    ) -> AsyncIterator[ServerSentEvent]:
        for event in events:
            yield ServerSentEvent(raw_data=event.model_dump_json(), id=str(event.seq))

    return router
