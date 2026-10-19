"""Snapshot listing and revert. Revert is user-initiated, so it is not an approval."""

from fastapi import APIRouter, HTTPException

from tools.jail import JailError, workspace_root
from tools.snapshot import SnapshotError, SnapshotStore
from tools.types import RevertRequest, RevertResult, SnapshotEntry


def snapshot_routes() -> APIRouter:
    router = APIRouter()

    def store(workspace: str) -> SnapshotStore:
        try:
            return SnapshotStore(workspace_root(workspace))
        except (JailError, OSError):
            raise HTTPException(400, "Select an accessible workspace") from None

    @router.get("/snapshots")
    def snapshots(workspace: str) -> list[SnapshotEntry]:
        return [SnapshotEntry(**entry.model_dump()) for entry in store(workspace).entries()]

    @router.post("/snapshots/{snapshot_id}/revert")
    def revert(snapshot_id: str, value: RevertRequest) -> RevertResult:
        try:
            return store(value.workspace).revert(snapshot_id)
        except SnapshotError as error:
            raise HTTPException(404, str(error)) from None
        except (JailError, OSError):
            raise HTTPException(400, "Revert failed") from None

    return router
