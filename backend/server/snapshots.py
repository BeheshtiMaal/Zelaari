"""Snapshot listing and revert. Revert is user-initiated, so it is not an approval."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from permissions.types import ApprovalRecord, RulesFile
from store.actions import ActionApprovals
from store.secrets import Redactor
from tools.jail import JailError, workspace_root
from tools.snapshot import SnapshotError, SnapshotStore
from tools.types import RevertRequest, RevertResult, SnapshotEntry


def snapshot_routes(
    redactor: Redactor | None = None, actions: ActionApprovals | None = None
) -> APIRouter:
    router = APIRouter()

    def store(workspace: str) -> SnapshotStore:
        try:
            return SnapshotStore(workspace_root(workspace), redactor=redactor)
        except (JailError, OSError):
            raise HTTPException(400, "Select an accessible workspace") from None

    @router.get("/snapshots")
    def snapshots(workspace: str) -> list[SnapshotEntry]:
        return [SnapshotEntry(**entry.model_dump()) for entry in store(workspace).entries()]

    @router.post("/snapshots/{snapshot_id}/revert", response_model=RevertResult | ApprovalRecord)
    def revert(snapshot_id: str, value: RevertRequest) -> RevertResult | JSONResponse:
        try:
            snapshots = store(value.workspace)
            meta = snapshots.meta(snapshot_id)
            if meta.path.replace("\\", "/").casefold() == ".harness/rules.json":
                if actions is None:
                    raise HTTPException(409, "Rules restoration requires approval")
                previous = snapshots.content(snapshot_id)
                proposal = actions.propose_rules(
                    workspace_root(value.workspace),
                    RulesFile.model_validate_json(previous)
                    if previous is not None
                    else RulesFile(),
                    raw_content=previous.decode("utf-8") if previous is not None else None,
                    remove=previous is None,
                )
                return JSONResponse(status_code=202, content=proposal.model_dump(mode="json"))
            return snapshots.revert(snapshot_id)
        except SnapshotError as error:
            raise HTTPException(404, str(error)) from None
        except (JailError, OSError):
            raise HTTPException(400, "Revert failed") from None
        except ValueError:
            raise HTTPException(
                409, "Rules restoration cannot be proposed; inspect current rules"
            ) from None

    return router
