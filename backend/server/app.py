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
from pydantic import BaseModel, Field

from agent.events import Event, HealthResponse, RunRequest, RunResponse
from permissions.types import (
    ApprovalDecision,
    ApprovalRecord,
    ApprovalRequest,
    ApprovalResolution,
    UnknownApproval,
)
from planning.types import SteeringRecord, SteeringSubmission
from questions.types import QuestionDecision, QuestionRecord
from server.files import file_routes
from server.git import git_routes
from server.models import model_routes
from server.rules import rules_routes
from server.snapshots import snapshot_routes
from server.workspaces import workspace_routes
from store.actions import ActionApprovals
from store.catalog import Catalog
from store.secrets import Redactor


class RunService(Protocol):
    async def steer(self, run_id: str, value: SteeringSubmission) -> SteeringRecord: ...
    def questions(self, run_id: str) -> list[QuestionRecord]: ...
    async def answer_question(
        self, run_id: str, call_id: str, decision: QuestionDecision
    ) -> None: ...
    def retry_command(self, run_id: str, call_id: str, timeout: float) -> ApprovalRecord: ...
    def preview(
        self, run_id: str, approval_id: str, decision: ApprovalDecision
    ) -> ApprovalRequest: ...
    async def recover(self) -> None: ...
    def approvals(self, status: str | None = None) -> list[ApprovalRecord]: ...
    async def start(self, request: RunRequest) -> str: ...
    async def stop(self, run_id: str) -> None: ...
    async def resolve(
        self, run_id: str, approval_id: str, decision: ApprovalDecision
    ) -> str | None: ...
    def events(self, run_id: str, after: int) -> AsyncIterator[Event]: ...
    def contains(self, run_id: str) -> bool: ...
    def pending_paths(self) -> set[str]: ...
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
    app.include_router(snapshot_routes(catalog.redactor, ActionApprovals(catalog)))
    app.include_router(git_routes(ActionApprovals(catalog)))
    app.include_router(file_routes(lambda: service.pending_paths() if service else set()))
    app.include_router(rules_routes(ActionApprovals(catalog)))

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request: object, error: RequestValidationError) -> JSONResponse:
        # Pydantic errors contain input values, including submitted credentials.
        return JSONResponse({"detail": "Invalid request"}, status_code=422)

    @app.get("/health")
    def health() -> HealthResponse:
        return HealthResponse()

    @app.get("/approvals")
    async def approvals(status: str | None = None) -> list[ApprovalRecord]:
        manager = runs()
        await manager.recover()
        return manager.approvals(status)

    @app.post("/runs", status_code=201)
    async def create_run(request: RunRequest) -> JSONResponse:
        from agent.bridge import WorktreeApprovalRequired

        try:
            run_id = await runs().start(request)
        except WorktreeApprovalRequired as pending:
            # Nothing was created and no run exists yet: the client shows the modal and
            # repeats the request with `worktree_approved`.
            return JSONResponse(
                status_code=409,
                content={
                    "detail": "Worktree creation needs approval",
                    "approval": pending.approval.model_dump(mode="json"),
                },
            )
        except (ValueError, OSError):
            raise HTTPException(
                400, "Select an accessible workspace and configured model"
            ) from None
        return JSONResponse(status_code=201, content=RunResponse(run_id=run_id).model_dump())

    async def require_run(run_id: str) -> RunService:
        manager = runs()
        await manager.recover()
        if not manager.contains(run_id):
            raise HTTPException(404, "Unknown run")
        return manager

    @app.post("/runs/{run_id}/stop")
    async def stop_run(run_id: str) -> dict[str, str]:
        await (await require_run(run_id)).stop(run_id)
        return {"status": "ok"}

    @app.post("/runs/{run_id}/messages", status_code=202)
    async def steer_run(run_id: str, value: SteeringSubmission) -> SteeringRecord:
        manager = runs()
        await manager.recover()
        if not manager.contains(run_id):
            if any(task.id == run_id for task in catalog.data.workspaces.tasks):
                raise HTTPException(409, "Run is not available for steering")
            raise HTTPException(404, "Unknown run")
        try:
            return await manager.steer(run_id, value)
        except ValueError:
            raise HTTPException(409, "Run finished or submission identity conflicts") from None

    @app.post("/runs/{run_id}/interrupts/{approval_id}")
    async def resolve_approval(
        run_id: str,
        approval_id: str,
        decision: ApprovalDecision | QuestionDecision,
    ) -> ApprovalResolution:
        manager = await require_run(run_id)
        try:
            if isinstance(decision, QuestionDecision):
                await manager.answer_question(run_id, approval_id, decision)
                resumed_run_id = None
            else:
                resumed_run_id = await manager.resolve(run_id, approval_id, decision)
        except UnknownApproval:
            # Already answered, or never pending: the caller must re-read the stream
            # rather than have a decision silently applied twice.
            raise HTTPException(409, "Unknown or already-resolved approval") from None
        except (ValueError, OSError):
            raise HTTPException(
                409, "Review is stale or invalid; refresh before deciding"
            ) from None
        return ApprovalResolution(run_id=resumed_run_id)

    @app.get("/runs/{run_id}/questions")
    async def questions(run_id: str) -> list[QuestionRecord]:
        manager = runs()
        await manager.recover()
        try:
            return manager.questions(run_id)
        except (ValueError, OSError):
            raise HTTPException(404, "Question history is unavailable") from None

    @app.post("/runs/{run_id}/interrupts/{approval_id}/preview")
    async def preview_approval(
        run_id: str, approval_id: str, decision: ApprovalDecision
    ) -> ApprovalRequest:
        try:
            return (await require_run(run_id)).preview(run_id, approval_id, decision)
        except (UnknownApproval, ValueError, OSError):
            raise HTTPException(
                409, "Input cannot be reviewed; refresh and check permissions"
            ) from None

    @app.post("/runs/{run_id}/commands/{call_id}/retry", status_code=202)
    async def retry_command(run_id: str, call_id: str, value: RetryCommand) -> ApprovalRecord:
        try:
            return runs().retry_command(run_id, call_id, value.timeout)
        except (ValueError, OSError):
            raise HTTPException(
                409, "Command cannot be retried under current permissions"
            ) from None

    @app.get("/runs/{run_id}/events", response_class=EventSourceResponse)
    async def events(
        run_id: str,
        manager: Annotated[RunService, Depends(require_run)],
        last_event_id: Annotated[int, Header(ge=0)] = 0,
    ) -> AsyncIterator[ServerSentEvent]:
        async for event in manager.events(run_id, last_event_id):
            yield ServerSentEvent(raw_data=event.model_dump_json(), id=str(event.seq))

    return app


class RetryCommand(BaseModel):
    timeout: float = Field(default=300, ge=1, le=600)
