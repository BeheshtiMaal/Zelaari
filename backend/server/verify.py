"""Workspace verification settings. A save is always a separately reviewed decision."""

from pathlib import Path

from fastapi import APIRouter, HTTPException

from permissions.types import ApprovalRecord
from store.actions import ActionApprovals
from tools.jail import JailError, workspace_root
from verify.settings import VerifyConfig, VerifySettingsResponse, load_config, response


def _root(value: str) -> Path:
    try:
        return workspace_root(value)
    except (JailError, ValueError, OSError):
        raise HTTPException(400, "Select an accessible workspace") from None


def verify_routes(actions: ActionApprovals) -> APIRouter:
    router = APIRouter()

    @router.get("/verify/settings")
    def read_settings(workspace: str) -> VerifySettingsResponse:
        root = _root(workspace)
        return response(root, load_config(root))

    @router.put("/verify/settings", status_code=202)
    def write_settings(workspace: str, value: VerifyConfig) -> ApprovalRecord:
        try:
            return actions.propose_verify(_root(workspace), value)
        except (OSError, ValueError):
            raise HTTPException(409, "Workspace configuration needs repair") from None

    return router
