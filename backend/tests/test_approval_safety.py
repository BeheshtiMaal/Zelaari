"""Review binding and write-ahead recovery tests, including forged edit paths."""

import asyncio
from pathlib import Path
from typing import Any, cast

import pytest
from langchain.agents.middleware.types import ToolCallRequest
from langchain_core.messages import ToolMessage

from permissions.middleware import PermissionMiddleware
from permissions.review import arguments_digest, prepare_review
from permissions.rules import RulesEngine
from permissions.types import ApprovalDecision, ApprovalRequest, RulesFile
from store.actions import ActionApprovals
from store.catalog import Catalog
from store.effects import EffectJournal
from tools.jail import storage_path


def test_diff_revision_binds_bytes_arguments_and_no_trailing_newline(tmp_path: Path) -> None:
    path = tmp_path / "a.txt"
    path.write_bytes(b"old\r\nlast")
    request = ApprovalRequest(
        approval_id="one",
        run_id="run",
        kind="tool",
        tool="edit_file",
        path="a.txt",
        args={"old_string": "old", "new_string": "new"},
    )
    review = prepare_review(tmp_path, request)
    assert "-old\r\n+new\r\n" in review.diff
    assert "\\ No newline at end of file" in review.diff
    path.write_bytes(b"changed\r\nlast")
    with pytest.raises(ValueError):
        prepare_review(tmp_path, request)


@pytest.mark.parametrize("completed", [False, True])
def test_journal_prevents_dispatch_after_uncertain_or_completed_effect(
    tmp_path: Path,
    completed: bool,
) -> None:
    args = {"command": "Write-Output fixture"}
    journal = EffectJournal(storage_path(tmp_path, "runs/run/effects.json"))
    journal.begin("one", arguments_digest(args))
    if completed:
        journal.complete("one", "original result")
    gate = PermissionMiddleware(RulesEngine.load(tmp_path, "auto"), run_id="run")
    request = ToolCallRequest(
        tool_call={"name": "run_command", "args": args, "id": "one", "type": "tool_call"},
        tool=None,
        state={"messages": []},
        runtime=cast(Any, None),
    )

    async def never(inner: ToolCallRequest) -> ToolMessage:
        raise AssertionError("recovered effect was dispatched again")

    result = asyncio.run(gate.awrap_tool_call(request, never))
    assert isinstance(result, ToolMessage)
    assert (
        str(result.content) == "original result"
        if completed
        else "Interrupted:" in str(result.content)
    )


def test_rules_proposal_reject_and_stale_revision_never_write(tmp_path: Path) -> None:
    actions = ActionApprovals(Catalog())
    proposal = actions.propose_rules(tmp_path, RulesFile(mode="auto"))
    assert not storage_path(tmp_path, "rules.json").exists()
    actions.resolve(
        proposal.request.run_id, proposal.request.approval_id, ApprovalDecision(decision="reject")
    )
    assert not storage_path(tmp_path, "rules.json").exists()
    proposal = actions.propose_rules(tmp_path, RulesFile(mode="auto"))
    RulesEngine.load(tmp_path).save(RulesFile(mode="read-only"))
    with pytest.raises(ValueError, match="changed"):
        actions.resolve(
            proposal.request.run_id,
            proposal.request.approval_id,
            ApprovalDecision(decision="approve"),
        )
    assert RulesEngine.load(tmp_path).mode == "read-only"
