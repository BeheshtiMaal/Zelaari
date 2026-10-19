"""Authenticated REST and SSE transport. No engine work runs at import time."""

import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Protocol

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent

from agent.events import Event, HealthResponse, RunRequest, RunResponse
from permissions.types import ApprovalDecision, UnknownApproval
from server.models import model_routes
from server.snapshots import snapshot_routes
from server.workspaces import workspace_routes
from store.catalog import Catalog
from store.secrets import Redactor


class RunService(Protocol):
    async def start(self, request: RunRequest) -> str: ...
    async def stop(self, run_id: str) -> None: ...
    async def resolve(
        self, run_id: str, approval_id: str, decision: ApprovalDecision
    ) -> None: ...
    def events(self, run_id: str, after: int) -> AsyncIterator[Event]: ...
    def contains(self, run_id: str) -> bool: ...
    async def close(self) -> None: ...


def create_app(
    token: str,
    service: RunService | None = None,
    *,
    dev: bool = False,
    catalog: Catalog | None = None,
    app_data: Path | None = None,
) -> FastAPI:
    if not token and not dev:
        raise ValueError("A per-launch token is required")
    catalog = catalog or Catalog(app_data / "catalog.json" if app_data else None, Redactor([token]))

    def runs() -> RunService:
        nonlocal service
        if service is None:
            from agent.bridge import RunManager

            service = RunManager(secrets_to_redact=[token], catalog=catalog)
        return service

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        if service is not None:
            await service.close()

    def authorize(authorization: Annotated[str | None, Header()] = None) -> None:
        if not dev and not secrets.compare_digest(authorization or "", f"Bearer {token}"):
            raise HTTPException(401, "Unauthorized")

    app = FastAPI(
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        dependencies=[Depends(authorize)],
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["app://codeharness", "http://localhost:3000"],
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Authorization", "Last-Event-ID", "Content-Type"],
    )
    app.include_router(model_routes(catalog))
    app.include_router(workspace_routes(catalog))
    app.include_router(snapshot_routes())

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request: object, error: RequestValidationError) -> JSONResponse:
        # Pydantic errors contain input values, including submitted credentials.
        return JSONResponse({"detail": "Invalid request"}, status_code=422)

    @app.get("/health")
    def health() -> HealthResponse:
        return HealthResponse()

    @app.post("/runs", status_code=201)
    async def create_run(request: RunRequest) -> RunResponse:
        try:
            return RunResponse(run_id=await runs().start(request))
        except (ValueError, OSError):
            raise HTTPException(
                400, "Select an accessible workspace and configured model"
            ) from None

    def require_run(run_id: str) -> RunService:
        manager = runs()
        if not manager.contains(run_id):
            raise HTTPException(404, "Unknown run")
        return manager

    @app.post("/runs/{run_id}/stop")
    async def stop_run(run_id: str) -> dict[str, str]:
        await require_run(run_id).stop(run_id)
        return {"status": "ok"}

    @app.post("/runs/{run_id}/interrupts/{approval_id}")
    async def resolve_approval(
        run_id: str,
        approval_id: str,
        decision: ApprovalDecision,
    ) -> dict[str, str]:
        manager = require_run(run_id)
        try:
            await manager.resolve(run_id, approval_id, decision)
        except UnknownApproval:
            # Already answered, or never pending: the caller must re-read the stream
            # rather than have a decision silently applied twice.
            raise HTTPException(409, "Unknown or already-resolved approval") from None
        return {"status": "ok"}

    @app.get("/runs/{run_id}/events", response_class=EventSourceResponse)
    async def events(
        run_id: str,
        manager: Annotated[RunService, Depends(require_run)],
        last_event_id: Annotated[int, Header(ge=0)] = 0,
    ) -> AsyncIterator[ServerSentEvent]:
        async for event in manager.events(run_id, last_event_id):
            yield ServerSentEvent(raw_data=event.model_dump_json(), id=str(event.seq))

    return app
