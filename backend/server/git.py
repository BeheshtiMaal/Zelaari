"""Git routes for the branch chip.

A switch started from the UI is the person's own action, so the click is the consent:
the rules grid can still deny it (read-only, or an explicit deny rule) but it does not
raise an approval, the same way a user-initiated rules edit does not.
"""

from fastapi import APIRouter, HTTPException

from permissions.rules import RulesEngine
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

    @router.post("/workspaces/branch")
    def switch_branch(value: BranchSwitch) -> BranchSwitchResult:
        try:
            root = workspace_root(value.workspace)
            branch = validate_branch(value.branch)
        except (ValueError, OSError) as error:
            raise HTTPException(400, str(error)) from None

        outcome = RulesEngine.load(root).decide("git_switch", command=f"git switch {branch}")
        if outcome.action == "deny":
            raise HTTPException(403, outcome.reason)

        result = switch(root, branch)
        if result.error:
            # The tree is untouched: git refuses a dirty switch before moving HEAD.
            raise HTTPException(409, result.error)
        return result

    return router
