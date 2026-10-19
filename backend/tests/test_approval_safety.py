"""Review binding and write-ahead recovery tests, including forged edit paths."""

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from langchain.agents.middleware.types import ToolCallRequest
from langchain_core.messages import ToolMessage

from permissions.middleware import PermissionMiddleware
from permissions.review import arguments_digest, prepare_review
from permissions.rules import RulesEngine
from permissions.types import ApprovalDecision, ApprovalRequest, PermissionOutcome, RulesFile
from server.app import create_app
from store.actions import ActionApprovals
from store.catalog import Catalog
from store.effects import EffectJournal
from store.secrets import Redactor
from tools.jail import resolve_virtual, storage_path
from tools.snapshot import SnapshotError, SnapshotStore


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
    assert "-old\r\n+new\n" in review.diff
    assert "\\ No newline at end of file" in review.diff
    path.write_bytes(b"changed\r\nlast")
    with pytest.raises(ValueError):
        prepare_review(tmp_path, request)


@pytest.mark.parametrize(
    ("before", "after", "tool"),
    [
        (None, "created\n", "write_file"),
        ("deleted\n", "", "delete"),
        ("", "", "delete"),
        ("", "filled\n", "write_file"),
        ("a\n" * 20 + "old\n", "new\n" + "a\n" * 19 + "changed\n", "write_file"),
    ],
)
def test_unified_review_for_create_delete_empty_and_multiple_hunks(
    tmp_path: Path,
    before: str | None,
    after: str,
    tool: str,
) -> None:
    if before is not None:
        (tmp_path / "a.txt").write_bytes(before.encode())
    request = ApprovalRequest(
        approval_id="one",
        run_id="run",
        kind="tool",
        tool=tool,
        path="a.txt",
        args={"content": after},
    )
    review = prepare_review(tmp_path, request)
    assert review.revision
    if before != after:
        assert "@@" in review.diff
    if before and len(before.splitlines()) > 10:
        assert review.diff.count("@@ -") == 2


def test_binary_delete_review_binds_original_bytes_without_decoding(tmp_path: Path) -> None:
    (tmp_path / "asset.bin").write_bytes(b"\xff\x00\xfe")
    request = ApprovalRequest(
        approval_id="one", run_id="run", kind="tool", tool="delete", path="asset.bin"
    )
    review = prepare_review(tmp_path, request)
    assert review.diff == "Binary files asset.bin and /dev/null differ\n"
    (tmp_path / "asset.bin").write_bytes(b"\xff\x01\xfe")
    assert prepare_review(tmp_path, request).revision != review.revision


def test_review_redacts_current_file_diff_and_policy_before_checkpoint_payload(
    tmp_path: Path,
) -> None:
    secret = "fixture-diff-canary-7261"
    (tmp_path / "a.txt").write_text(f"header\n{secret}\n")
    gate = PermissionMiddleware(
        RulesEngine.load(tmp_path), run_id="run", redactor=Redactor([secret])
    )
    request = gate.approval(
        {
            "name": "edit_file",
            "args": {"file_path": "a.txt", "old_string": "header", "new_string": "new header"},
            "id": "one",
            "type": "tool_call",
        },
        PermissionOutcome(action="ask", reason=f"policy {secret}"),
    )
    assert secret not in request.model_dump_json()
    assert "[REDACTED]" in request.diff


def test_rules_diff_never_copies_existing_credential_into_approval_ledger(tmp_path: Path) -> None:
    secret = "fixture-rules-diff-canary-3961"
    RulesEngine.load(tmp_path).save(RulesFile(tools={secret: []}))
    actions = ActionApprovals(Catalog(redactor=Redactor([secret])))
    proposal = actions.propose_rules(tmp_path, RulesFile())
    assert secret not in proposal.model_dump_json()
    assert secret.encode() not in storage_path(tmp_path, "action-approvals.json").read_bytes()
    with pytest.raises(ValueError):
        actions.resolve(
            proposal.request.run_id,
            proposal.request.approval_id,
            ApprovalDecision(decision="approve"),
        )
    assert not list(storage_path(tmp_path, "snapshots").glob("*/content.bin"))


def test_snapshots_refuse_registered_credentials_before_capture_and_restore(tmp_path: Path) -> None:
    secret = "fixture-snapshot-canary-7396"
    target = resolve_virtual(tmp_path, "a.txt")
    target.path.write_text(secret)
    store = SnapshotStore(tmp_path, redactor=Redactor([secret]))
    with pytest.raises(SnapshotError, match="protected credential"):
        store.capture(target, tool="edit_file")
    assert not store.entries()
    legacy = SnapshotStore(tmp_path)
    snapshot_id = legacy.capture(target, tool="edit_file")
    target.path.write_text("current safe content")
    with pytest.raises(SnapshotError, match="protected credential"):
        store.revert(snapshot_id)
    assert target.path.read_text() == "current safe content"


def test_snapshot_metadata_cannot_redirect_undo_outside_workspace(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "a.txt").write_text("inside")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside unchanged")
    store = SnapshotStore(root)
    identity = store.capture(resolve_virtual(root, "a.txt"), tool="edit_file")
    path = store.directory / identity / "meta.json"
    meta = json.loads(path.read_text())
    meta["path"] = "../outside.txt"
    path.write_text(json.dumps(meta))
    with pytest.raises(SnapshotError):
        store.revert(identity)
    assert outside.read_text() == "outside unchanged"
    assert not store.entries()


@pytest.mark.parametrize("artifact", ["meta.json", "content.bin"])
def test_snapshot_artifact_symlink_cannot_read_outside_workspace(
    tmp_path: Path, artifact: str
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    target = resolve_virtual(root, "a.txt")
    target.path.write_text("original")
    store = SnapshotStore(root)
    identity = store.capture(target, tool="edit_file")
    target.path.write_text("current unchanged")
    source = store.directory / identity / artifact
    outside = tmp_path / "outside.txt"
    outside.write_bytes(source.read_bytes())
    source.unlink()
    source.symlink_to(outside)
    with pytest.raises(SnapshotError):
        store.revert(identity)
    assert target.path.read_text() == "current unchanged"


@pytest.mark.parametrize("previous", [None, b'{\r\n "mode": "ask", "tools": {}\r\n}\r\n'])
def test_rules_undo_is_reviewed_before_exact_restoration(
    tmp_path: Path, previous: bytes | None
) -> None:
    target = resolve_virtual(tmp_path, ".harness/rules.json", allow_protected=True)
    if previous is not None:
        target.path.parent.mkdir(parents=True)
        target.path.write_bytes(previous)
    store = SnapshotStore(tmp_path)
    identity = store.capture(target, tool="rules_update")
    RulesEngine.load(tmp_path).save(RulesFile(mode="auto"))
    current = target.path.read_bytes()
    with pytest.raises(SnapshotError, match="approval"):
        store.revert(identity)
    headers = {"Authorization": "Bearer token"}
    with TestClient(create_app("token")) as client:

        def proposal() -> dict[str, Any]:
            result = client.post(
                f"/snapshots/{identity}/revert", headers=headers, json={"workspace": str(tmp_path)}
            )
            assert result.status_code == 202, result.text
            return cast(dict[str, Any], result.json()["request"])

        request = proposal()
        assert target.path.read_bytes() == current
        result = client.post(
            f"/runs/{request['run_id']}/interrupts/{request['approval_id']}",
            headers=headers,
            json={"decision": "reject"},
        )
        assert result.status_code == 200
        assert target.path.read_bytes() == current
        request = proposal()
        result = client.post(
            f"/runs/{request['run_id']}/interrupts/{request['approval_id']}",
            headers=headers,
            json={"decision": "approve", "revision": request["revision"]},
        )
        assert result.status_code == 200, result.text
    if previous is None:
        assert not target.path.exists()
    else:
        assert target.path.read_bytes() == previous


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


def test_configuration_proposals_from_route_threads_do_not_overwrite_each_other(
    tmp_path: Path,
) -> None:
    catalog = Catalog()
    services = [ActionApprovals(catalog), ActionApprovals(catalog)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        proposals = list(
            pool.map(
                lambda index: services[index % 2].propose_rules(tmp_path, RulesFile(mode="auto")),
                range(12),
            )
        )
    assert len({record.request.approval_id for record in proposals}) == 12
    assert len(services[0].records()) == 12
    assert all(record.status == "pending" for record in services[0].records())
