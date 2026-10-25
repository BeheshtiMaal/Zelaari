from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.sse import EventSourceResponse, ServerSentEvent

from agent.events import Event
from appdata import sample
from providers.base import WorkspaceSelection, WorkspaceState
from store.catalog import Catalog
from store.workspaces import select_workspace, task_events, workspace_state


def workspace_routes(catalog: Catalog, app_data: Path | None = None) -> APIRouter:
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

    @router.post("/workspaces/sample")
    def open_sample() -> WorkspaceState:
        """Materialise the bundled sample into app data and open it.

        It is a copy, not the app's own files: a workspace must be a project the person
        can edit, and a second click must not undo what they changed.
        """
        bundle = sample.source()
        if app_data is None or bundle is None:
            raise HTTPException(404, "This build does not include the sample project")
        try:
            destination = sample.materialise(bundle, app_data)
            return select_workspace(catalog, str(destination))
        except (ValueError, OSError, RuntimeError):
            raise HTTPException(400, "The sample project could not be opened") from None

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
