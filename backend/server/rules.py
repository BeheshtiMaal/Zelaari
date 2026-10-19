"""Rules routes (R18).

The grid is the person's own configuration, so a save here is consent in itself: no
approval is raised. It is still a write into `.harness/`, which means the engine
validates the whole file before anything reaches disk and an unreadable file is
reported rather than silently replaced.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException

from permissions.rules import DEFAULTS, RulesEngine
from permissions.types import RulesFile
from tools.jail import JailError, workspace_root
from tools.types import RulesResponse


def _response(engine: RulesEngine) -> RulesResponse:
    return RulesResponse(
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


def rules_routes() -> APIRouter:
    router = APIRouter()

    @router.get("/rules")
    def read_rules(workspace: str) -> RulesResponse:
        """The effective grid. A malformed file still answers, with `mode` asked."""
        return _response(RulesEngine.load(_root(workspace)))

    @router.put("/rules")
    def write_rules(workspace: str, value: RulesFile) -> RulesResponse:
        root = _root(workspace)
        engine = RulesEngine.load(root)
        try:
            engine.save(value)
        except (OSError, ValueError) as error:
            raise HTTPException(409, f"Could not write rules: {error}") from None
        return _response(RulesEngine.load(root))

    return router
