"""Rules reads and staged changes. A save always requires a separate reviewed decision."""

from pathlib import Path

from fastapi import APIRouter, HTTPException

from permissions.rules import DEFAULTS, RulesEngine
from permissions.types import ApprovalRecord, RulesFile
from store.actions import ActionApprovals
from tools.jail import JailError, workspace_root
from tools.types import RulesResponse


def _response(engine: RulesEngine) -> RulesResponse:
    return RulesResponse(
        rules=engine.rules,
        mode=engine.mode,
        tools={
            tool: [rule.model_dump() for rule in rules]
            for tool, rules in engine.rules.tools.items()
        },
        defaults={key: value for key, value in DEFAULTS[engine.mode].items()},
        always_ask=engine.always_ask(),
    )


def _root(value: str) -> Path:
    try:
        return workspace_root(value)
    except (JailError, ValueError, OSError):
        raise HTTPException(400, "Select an accessible workspace") from None


def rules_routes(actions: ActionApprovals) -> APIRouter:
    router = APIRouter()

    @router.get("/rules")
    def read_rules(workspace: str) -> RulesResponse:
        """The effective grid. A malformed file still answers, with `mode` asked."""
        return _response(RulesEngine.load(_root(workspace)))

    @router.put("/rules", status_code=202)
    def write_rules(workspace: str, value: RulesFile) -> ApprovalRecord:
        root = _root(workspace)
        try:
            return actions.propose_rules(root, value)
        except (OSError, ValueError):
            raise HTTPException(
                409, "Could not propose rules; check the workspace rules file"
            ) from None

    return router
