"""Git routes for the branch chip, including the pre-execution approval gate."""

from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from permissions.rules import RulesEngine
from permissions.types import ApprovalRequest
from tools.git import list_branches, switch, validate_branch
from tools.jail import workspace_root
from tools.types import BranchList, BranchSwitch, BranchSwitchResult


def git_routes() -> APIRouter:
    router = APIRouter()

    @router.get("/workspaces/branches")
    def branches(workspace: str) -> BranchList:
        try:
            return list_branches(workspace_root(workspace))
        except (ValueError, OSError):
            raise HTTPException(400, "Select an accessible workspace") from None

    @router.post("/workspaces/branch", response_model=BranchSwitchResult)
    def switch_branch(value: BranchSwitch) -> BranchSwitchResult | JSONResponse:
        try:
            root = workspace_root(value.workspace)
            branch = validate_branch(value.branch)
        except (ValueError, OSError) as error:
            raise HTTPException(400, str(error)) from None

        command = f"git switch {branch}"
        outcome = RulesEngine.load(root, value.mode).decide("git_switch", command=command)
        if outcome.action == "deny":
            raise HTTPException(403, outcome.reason)
        if outcome.action == "ask" and not value.approved:
            approval = ApprovalRequest(
                approval_id=uuid4().hex,
                run_id="",
                kind="command",
                tool="git_switch",
                command=command,
                risk=outcome.risk,
                reason=outcome.reason,
            )
            return JSONResponse(
                status_code=409,
                content={
                    "detail": "Branch switch needs approval",
                    "approval": approval.model_dump(),
                },
            )

        result = switch(root, branch)
        if result.error:
            # The tree is untouched: git refuses a dirty switch before moving HEAD.
            raise HTTPException(409, result.error)
        return result

    return router
