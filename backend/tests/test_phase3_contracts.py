"""Phase 3 wire contracts: approval events, new request fields and generated-schema coverage."""

import json

import pytest
from pydantic import ValidationError

from agent.events import (
    ApprovalRequested,
    ApprovalResolved,
    Protocol,
    RunRequest,
    event_adapter,
)
from permissions.types import ApprovalDecision, ApprovalRequest, RiskAssessment, Rule, RulesFile
from tools.types import CommandResult, FileListing


def _approval() -> ApprovalRequest:
    return ApprovalRequest(
        approval_id="call-1",
        run_id="run-1",
        kind="command",
        tool="run_command",
        command="npm install",
        risk=RiskAssessment(level="high", reasons=["package install"]),
        reason="Package installation changes the dependency tree",
    )


def test_approval_events_roundtrip_through_the_union() -> None:
    requested = ApprovalRequested(run_id="run-1", seq=1, approval=_approval())
    resolved = ApprovalResolved(
        run_id="run-1", seq=2, approval_id="call-1", decision="reject", reason="not now"
    )

    for event in (requested, resolved):
        parsed = event_adapter.validate_json(event.model_dump_json())
        assert parsed == event
        assert parsed.type == event.type


def test_approval_events_are_discriminated_not_future_events() -> None:
    schema = Protocol.model_json_schema()
    assert "discriminator" in schema["properties"]["event"]
    # A payload carrying `approval` must select the typed event, not FutureEvent.
    approval = _approval().model_dump()
    payload = {"type": "approval.requested", "run_id": "r", "seq": 1, "approval": approval}
    parsed = event_adapter.validate_python(payload)
    assert isinstance(parsed, ApprovalRequested)


def test_run_request_worktree_defaults_to_false_and_old_payloads_still_parse() -> None:
    legacy = {"task": "fix it", "workspace": "C:/work", "model": "demo", "mode": "ask"}
    assert RunRequest.model_validate(legacy).worktree is False

    modern = RunRequest.model_validate({**legacy, "worktree": True})
    assert modern.worktree is True


def test_unknown_permission_keys_are_rejected() -> None:
    with pytest.raises(ValidationError):
        RulesFile.model_validate({"mode": "ask", "tools": {}, "extra": 1})
    with pytest.raises(ValidationError):
        Rule.model_validate({"glob": "*", "action": "maybe"})


def test_rule_glob_rejects_traversal() -> None:
    with pytest.raises(ValidationError):
        Rule.model_validate({"glob": "../secrets/*", "action": "deny"})


def test_approval_decision_rejects_unknown_verdict() -> None:
    with pytest.raises(ValidationError):
        ApprovalDecision.model_validate({"decision": "maybe"})


def test_command_and_file_contracts_serialize() -> None:
    result = CommandResult(
        command="npm test", shell="powershell", exit_code=1, output="FAIL", total_lines=1
    )
    assert json.loads(result.model_dump_json())["shell"] == "powershell"

    listing = FileListing(path="src", kind="dir", entries=[])
    assert listing.file is None
    assert listing.model_dump()["kind"] == "dir"


def test_protocol_envelope_covers_phase_3_types() -> None:
    properties = Protocol.model_json_schema()["properties"]
    for name in (
        "approval_request",
        "command_result",
        "file_listing",
        "revert_result",
        "snapshot_entry",
        "branch_switch",
        "rules_response",
    ):
        assert name in properties
