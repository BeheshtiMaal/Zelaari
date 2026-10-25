"""What the app keeps on this device, and the one route that removes it."""

from collections.abc import Callable
from pathlib import Path

from fastapi import APIRouter, HTTPException

from appdata.retention import checkpoint_files, clear, run_bytes, run_directories
from appdata.types import DataSummary, DeletedRuns, WorkspaceData
from store.catalog import Catalog
from tools.jail import JailError, storage_path, workspace_root

MAX_WORKSPACES = 20


def _root(value: str) -> Path:
    try:
        return workspace_root(value)
    except (JailError, ValueError, OSError):
        raise HTTPException(400, "Select an accessible workspace") from None


def _recent(value: str) -> Path | None:
    """A recent workspace that was moved or deleted is skipped, not fatal."""
    try:
        return workspace_root(value)
    except (JailError, ValueError, OSError):
        return None


def _checkpoints(root: Path) -> int:
    return sum(path.stat().st_size for path in checkpoint_files(root) if path.exists())


def _workspace(root: Path, tasks: int) -> WorkspaceData:
    return WorkspaceData(
        path=str(root),
        name=root.name,
        harness=str(storage_path(root, "")),
        runs=len(run_directories(root)),
        run_bytes=run_bytes(root),
        checkpoints_bytes=_checkpoints(root),
        tasks=tasks,
    )


def data_routes(catalog: Catalog, app_data: Path | None, busy: Callable[[], bool]) -> APIRouter:
    router = APIRouter()

    @router.get("/data")
    def summary(workspace: str | None = None) -> DataSummary:
        """Counts only: no path inside a run, no prompt text, no command output."""
        recent = catalog.data.workspaces.recent[:MAX_WORKSPACES]
        roots = (
            [_root(workspace)]
            if workspace
            else [root for root in (_recent(item.path) for item in recent) if root is not None]
        )
        tasks = catalog.data.workspaces.tasks
        return DataSummary(
            app_data=str(app_data) if app_data else "",
            retention_days=catalog.data.settings.retention_days,
            keys=len(catalog.data.key_digests),
            workspaces=[
                _workspace(root, sum(1 for task in tasks if task.workspace == str(root)))
                for root in roots
            ],
        )

    @router.delete("/data/runs")
    def clear_runs(workspace: str) -> DeletedRuns:
        """Remove this workspace's run history.

        Run folders and the checkpoint database live under `.harness`, which is engine
        storage; nothing else in the workspace is read or removed. A live run refuses the
        request instead of deleting the folder it is still writing.
        """
        root = _root(workspace)
        if busy():
            raise HTTPException(409, "Stop the running task first")
        runs, freed = clear(root)
        kept = [task for task in catalog.data.workspaces.tasks if task.workspace != str(root)]
        removed = len(catalog.data.workspaces.tasks) - len(kept)
        if removed:
            catalog.data.workspaces.tasks = kept
            catalog.persist()
        return DeletedRuns(workspace=str(root), runs=runs, bytes=freed, tasks=removed)

    return router
