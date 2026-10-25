"""Content-bound previews. No filesystem mutation occurs while preparing a review."""

import difflib
import hashlib
import json
from pathlib import Path
from typing import Any

from agents import loader as agents
from agents import memory
from connectors.config import McpFile
from connectors.config import merged as merged_mcp
from permissions.classifier import assess
from permissions.types import ApprovalRequest, RiskAssessment
from planning.policy import merged_settings
from planning.review import plan_review
from planning.types import PlanningSettings, PlanSubmission
from skills import install as skill_install
from skills.search import SearchSettings
from skills.settings import merged_search
from tools.jail import MAX_TEXT_BYTES, resolve_virtual
from verify.settings import (
    ContextSettings,
    TerminalSettings,
    VerifyConfig,
    VerifySettings,
    merged_config,
)

MCP_TOOLS = frozenset({"mcp_server_add", "mcp_server_update", "mcp_server_delete"})
AGENT_TOOLS = frozenset({"agent_create", "agent_edit"})
PROTECTED_TOOLS = frozenset(
    {
        "rules_update",
        "planning_settings_update",
        "verify_settings_update",
        "search_settings_update",
        "skill_install",
        "skill_create",
        "skill_edit",
        "skill_delete",
        "agent_delete",
        "memory_update",
        *MCP_TOOLS,
        *AGENT_TOOLS,
    }
)
REVIEWED_TOOLS = frozenset({"write_file", "edit_file", "delete"}) | PROTECTED_TOOLS
CONTENT_TOOLS = frozenset(
    {
        "write_file",
        "rules_update",
        "planning_settings_update",
        "verify_settings_update",
        "search_settings_update",
        "memory_update",
        *MCP_TOOLS,
        *AGENT_TOOLS,
    }
)


def prepare_review(root: Path, request: ApprovalRequest) -> ApprovalRequest:
    before: bytes | None = None
    resolved_path: str | None = None
    after = ""
    material, plan_diff = plan_review(
        root, request.tool, request.args, request.plan_before, request.step_id
    )
    request = request.model_copy(update={"diff": plan_diff})
    if material is not None:
        request = request.model_copy(
            update={
                "plan_proposed": material["submission"],
                "plan_file_scope": material["file_scope"],
            }
        )
        proposed_plan = PlanSubmission.model_validate(material["submission"])
        risky = any(
            step.high_risk
            or (step.verify_command and assess(step.verify_command, root).level == "high")
            for step in proposed_plan.steps
        )
        if risky:
            request = request.model_copy(
                update={
                    "risk": RiskAssessment(
                        level="high",
                        reasons=list(dict.fromkeys([*request.risk.reasons, "high-risk plan step"])),
                    )
                }
            )
        elif request.tool == "submit_plan":
            request = request.model_copy(update={"risk": RiskAssessment()})
    if request.tool == "planning_settings_update":
        proposed_config = json.loads(str(request.args.get("content", "")))
        if not isinstance(proposed_config, dict):
            raise ValueError("Workspace config must be an object")
        settings = PlanningSettings.model_validate(proposed_config.get("planning"))
        if json.loads(merged_settings(root, settings)) != proposed_config:
            raise ValueError("Only planning settings may be changed by this proposal")
    if request.tool == "verify_settings_update":
        proposed_config = json.loads(str(request.args.get("content", "")))
        if not isinstance(proposed_config, dict):
            raise ValueError("Workspace config must be an object")
        verify_settings = VerifyConfig(
            context=ContextSettings.model_validate(proposed_config.get("context")),
            verify=VerifySettings.model_validate(proposed_config.get("verify")),
            terminal=TerminalSettings.model_validate(proposed_config.get("terminal")),
        )
        if json.loads(merged_config(root, verify_settings)) != proposed_config:
            raise ValueError("Only verification settings may be changed by this proposal")
    if request.tool in {"skill_install", "skill_create", "skill_edit"}:
        files = request.args.get("files")
        if not isinstance(files, dict) or "SKILL.md" not in files:
            raise ValueError("A skill proposal needs a SKILL.md")
        skill_install.candidate({str(key): str(value) for key, value in files.items()})
    if request.tool == "search_settings_update":
        proposed_config = json.loads(str(request.args.get("content", "")))
        if not isinstance(proposed_config, dict):
            raise ValueError("Workspace config must be an object")
        search = SearchSettings.model_validate(proposed_config.get("search") or {})
        if json.loads(merged_search(root, search)) != proposed_config:
            raise ValueError("Only search settings may be changed by this proposal")
    if request.tool in MCP_TOOLS:
        content = str(request.args.get("content", ""))
        proposed = McpFile.model_validate_json(content)
        if json.loads(merged_mcp(proposed.servers)) != json.loads(content):
            raise ValueError("Only MCP servers may be changed by this proposal")
    if request.tool in AGENT_TOOLS:
        content = str(request.args.get("content", ""))
        problem = agents.parse(content, str(request.args.get("name", "")))
        if isinstance(problem, str):
            raise ValueError(problem)
    if request.tool == "memory_update":
        if len(str(request.args.get("content", "")).encode("utf-8")) > memory.LIMIT:
            raise ValueError(f"Memory is limited to {memory.LIMIT} bytes")
    if request.path and request.tool in REVIEWED_TOOLS:
        target = resolve_virtual(
            root,
            request.path,
            allow_protected=request.tool in PROTECTED_TOOLS,
        ).path
        resolved_path = str(target)
        if target.is_file():
            if target.stat().st_size > MAX_TEXT_BYTES:
                raise ValueError("File is too large to review")
            before = target.read_bytes()
        binary_delete = request.tool == "delete" and before is not None and b"\x00" in before
        try:
            text = before.decode("utf-8") if before is not None else ""
        except UnicodeError:
            if request.tool != "delete":
                raise ValueError("Only text files can be edited") from None
            binary_delete = True
            text = ""
        if request.tool in CONTENT_TOOLS:
            after = str(request.args.get("content", ""))
        elif request.tool in {"skill_install", "skill_create", "skill_edit"}:
            files = request.args.get("files")
            after = str(files.get("SKILL.md", "")) if isinstance(files, dict) else ""
        elif request.tool == "skill_delete":
            after = ""
        elif request.tool == "agent_delete":
            after = ""
        elif request.tool == "edit_file":
            # WorkspaceBackend.edit uses read_text's universal newline conversion.
            # Preview exactly that operation while retaining raw bytes for the revision.
            editable = text.replace("\r\n", "\n").replace("\r", "\n")
            old, new = request.args.get("old_string"), request.args.get("new_string")
            if not isinstance(old, str) or not old or not isinstance(new, str):
                raise ValueError("Edit requires old_string and new_string")
            count = editable.count(old)
            if count == 0 or (count > 1 and not request.args.get("replace_all")):
                raise ValueError("Edit does not uniquely match the current file")
            after = editable.replace(old, new, -1 if request.args.get("replace_all") else 1)
        lines = difflib.unified_diff(
            text.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=request.path,
            tofile=request.path,
        )
        request = request.model_copy(
            update={
                "diff": (
                    f"Binary files {request.path} and /dev/null differ\n"
                    if binary_delete
                    else "".join(
                        line if line.endswith("\n") else line + "\n\\ No newline at end of file\n"
                        for line in lines
                    )
                    + ("\n" + plan_diff if plan_diff else "")
                )
            }
        )
    digest = hashlib.sha256(
        json.dumps(
            {
                "tool": request.tool,
                "args": request.args,
                "before": before.hex() if before is not None else None,
                "resolved_path": resolved_path,
                **({"planning": material} if material is not None else {}),
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    return request.model_copy(update={"revision": digest})


def arguments_digest(args: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(args, sort_keys=True).encode()).hexdigest()
