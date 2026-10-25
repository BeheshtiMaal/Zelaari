"""Durable approvals for user-initiated configuration changes, without a model run."""

import shutil
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from threading import RLock
from typing import Literal, cast
from uuid import uuid4

from pydantic import JsonValue

from agents import loader as agents
from agents import memory
from connectors.config import McpFile, McpServerConfig
from connectors.config import merged as merged_mcp
from permissions.review import prepare_review
from permissions.rules import RulesEngine
from permissions.types import (
    ApprovalAnswer,
    ApprovalDecision,
    ApprovalRecord,
    ApprovalRequest,
    Mode,
    RulesFile,
    UnknownApproval,
)
from planning.policy import merged_settings
from planning.types import PlanningSettings
from skills import install
from skills.registry import Registry
from skills.search import SearchSettings
from skills.settings import merged_search
from skills.types import AgentWriteInput, SkillWriteInput
from store.approvals import ApprovalLedger
from store.catalog import Catalog
from store.workspaces import select_workspace
from tools.atomic import atomic_write
from tools.git import switch, validate_branch
from tools.jail import resolve_virtual, storage_path, workspace_root
from tools.snapshot import SnapshotError, SnapshotStore
from verify.settings import VerifyConfig, merged_config

_lock = RLock()


def serialized[**P, T](function: Callable[P, T]) -> Callable[P, T]:
    @wraps(function)
    def execute(*args: P.args, **kwargs: P.kwargs) -> T:
        with _lock:
            return function(*args, **kwargs)

    return execute


class ActionApprovals:
    def __init__(self, catalog: Catalog) -> None:
        self.catalog = catalog

    def ledgers(self) -> list[ApprovalLedger]:
        result = []
        for workspace in self.catalog.data.workspaces.recent:
            try:
                result.append(
                    ApprovalLedger(
                        storage_path(workspace_root(workspace.path), "action-approvals.json")
                    )
                )
            except (OSError, ValueError):
                continue
        return result

    @serialized
    def records(self) -> list[ApprovalRecord]:
        return [record for ledger in self.ledgers() for record in ledger.records.values()]

    @serialized
    def recover(self) -> None:
        for ledger in self.ledgers():
            changed = False
            for record in ledger.records.values():
                if record.execution_status == "running":
                    record.execution_status = "interrupted"
                    record.result = "Interrupted: this action may have run. It was not replayed."
                    changed = True
            if changed:
                ledger.save()

    @serialized
    def find(self, run_id: str, approval_id: str) -> tuple[ApprovalLedger, ApprovalRecord]:
        for ledger in self.ledgers():
            record = ledger.records.get(approval_id)
            if record and record.request.run_id == run_id:
                return ledger, record
        raise UnknownApproval(approval_id)

    @serialized
    def preview(self, run_id: str, approval_id: str, decision: ApprovalDecision) -> ApprovalRequest:
        ledger, record = self.find(run_id, approval_id)
        if record.status != "pending":
            raise UnknownApproval(approval_id)
        request = record.request
        root = workspace_root(request.workspace)
        args = decision.edited_args if decision.edited_args is not None else request.args
        if self.catalog.redactor.value(args) != args:
            raise ValueError("Secret in proposed arguments")
        if request.tool == "planning_settings_update":
            if set(args) != {"content"}:
                raise ValueError("Invalid planning settings input")
            request = request.model_copy(update={"args": args})
        elif request.tool == "rules_update":
            if set(args) not in ({"content"}, {"content", "remove"}):
                raise ValueError("Invalid rules input")
            if args.get("remove") is True:
                if args["content"] != "":
                    raise ValueError("Removing rules cannot include replacement content")
            else:
                RulesFile.model_validate_json(str(args["content"]))
            request = request.model_copy(update={"args": args})
        elif request.tool in {"run_command", "git_switch"}:
            mode = request.args.get("mode")
            if args.get("mode") != mode:
                raise ValueError("Permission mode cannot be raised by editing arguments")
            if request.tool == "run_command":
                if set(args) - {"command", "timeout", "mode"}:
                    raise ValueError("Unknown command arguments")
                command = args.get("command")
                timeout = args.get("timeout", 120)
                if (
                    not isinstance(command, str)
                    or not command
                    or not isinstance(timeout, int | float)
                    or not 1 <= timeout <= 600
                ):
                    raise ValueError("Invalid command or timeout")
            else:
                if set(args) - {"branch", "mode"}:
                    raise ValueError("Unknown branch arguments")
                command = f"git switch {validate_branch(str(args.get('branch', '')))}"
                timeout = 120
            verdict = RulesEngine.load(root, cast(Mode | None, mode)).decide(
                request.tool, command=command, timeout=timeout
            )
            if verdict.action == "deny":
                raise ValueError("Current rules deny edited arguments")
            request = request.model_copy(
                update={
                    "args": args,
                    "command": command,
                    "risk": verdict.risk,
                }
            )
        else:
            raise ValueError("Create a new worktree proposal to change its input")
        prepared = prepare_review(root, request)
        record.request = ApprovalRequest.model_validate(
            self.catalog.redactor.value(prepared.model_dump(mode="json"))
        )
        ledger.save()
        return record.request

    def propose_rules(
        self, root: Path, value: RulesFile, *, raw_content: str | None = None, remove: bool = False
    ) -> ApprovalRecord:
        engine = RulesEngine.load(root)
        if engine.load_error:
            raise ValueError("Repair the unreadable rules file before proposing changes")
        if raw_content is not None:
            RulesFile.model_validate_json(raw_content)
        content = (
            ""
            if remove
            else raw_content
            if raw_content is not None
            else value.model_dump_json(indent=2)
        )
        if self.catalog.redactor.text(content) != content:
            raise ValueError("Secret in rules")
        select_workspace(self.catalog, str(root))
        identity = uuid4().hex
        request = prepare_review(
            root,
            ApprovalRequest(
                approval_id=identity,
                run_id=f"configuration-{identity}",
                kind="tool",
                tool="rules_update",
                path=".harness/rules.json",
                workspace=str(root),
                source_kind="configuration",
                source_title="Rules and permissions",
                reason="Changes to workspace permissions always require approval",
                policy_code="rules_change",
                args={"content": content, **({"remove": True} if remove else {})},
            ),
        )
        return self.propose(root, request)

    def propose_planning(self, root: Path, value: PlanningSettings) -> ApprovalRecord:
        content = merged_settings(root, value)
        if self.catalog.redactor.text(content) != content:
            raise ValueError("Secret in workspace configuration")
        return self.propose(
            root,
            ApprovalRequest(
                approval_id="",
                run_id="",
                kind="tool",
                tool="planning_settings_update",
                path=".harness/config.json",
                source_kind="configuration",
                source_title="Planning settings",
                policy_code="planning_settings_change",
                reason="Changes to engine configuration always require approval",
                args={"content": content},
            ),
        )

    def propose_verify(self, root: Path, value: VerifyConfig) -> ApprovalRecord:
        content = merged_config(root, value)
        if self.catalog.redactor.text(content) != content:
            raise ValueError("Secret in workspace configuration")
        return self.propose(
            root,
            ApprovalRequest(
                approval_id="",
                run_id="",
                kind="tool",
                tool="verify_settings_update",
                path=".harness/config.json",
                source_kind="configuration",
                source_title="Context and tests settings",
                policy_code="verify_settings_change",
                reason="Changes to engine configuration always require approval",
                args={"content": content},
            ),
        )

    def propose_search(self, root: Path, value: SearchSettings) -> ApprovalRecord:
        content = merged_search(root, value)
        if self.catalog.redactor.text(content) != content:
            raise ValueError("Secret in workspace configuration")
        return self.propose(
            root,
            ApprovalRequest(
                approval_id="",
                run_id="",
                kind="tool",
                tool="search_settings_update",
                path=".harness/config.json",
                source_kind="configuration",
                source_title="Web search",
                policy_code="search_settings_change",
                reason="Changes to engine configuration always require approval",
                args={"content": content},
            ),
        )

    def skill_folder(self, root: Path, name: str) -> Path:
        """Only `.harness/skills/<name>`, proven after resolution."""
        base = (root / ".harness" / "skills").resolve()
        folder = (base / name).resolve()
        if not folder.is_relative_to(base) or folder == base:
            raise ValueError("That skill folder is outside the workspace")
        return folder

    def propose_skill_install(
        self, root: Path, kind: str, source: str, app_data: Path | None
    ) -> ApprovalRecord:
        found = install.build(kind, source)
        existing = Registry.build(root, app_data).find(found.name)
        if existing is not None and existing.source == "workspace":
            raise ValueError("A skill with that name is already installed in this workspace")
        return self.propose_files(
            root,
            found.name,
            found.files,
            tool="skill_install",
            title=f"Install skill {found.name}",
            policy="skill_install",
            reason="Installing a skill writes files the agent may later follow",
            extra={"kind": kind, "source": source},
        )

    def propose_skill_write(
        self, root: Path, value: SkillWriteInput, *, create: bool
    ) -> ApprovalRecord:
        existing = Registry.build(root, None).find(value.name)
        if create:
            if existing is not None and existing.source == "workspace":
                raise ValueError("That skill already exists")
            files = install.from_write(
                value.name,
                value.description,
                value.body,
                value.command,
                value.category,
                value.requires_approval,
            )
        else:
            if existing is None or existing.source != "workspace":
                raise ValueError("Only a skill installed in this workspace can be edited")
            folder = self.skill_folder(root, value.name)
            files = install.from_folder(folder)
            files.update(
                install.from_write(
                    value.name,
                    value.description,
                    value.body,
                    value.command,
                    value.category,
                    value.requires_approval,
                )
            )
        checked = install.candidate(files)
        return self.propose_files(
            root,
            checked.name,
            checked.files,
            tool="skill_create" if create else "skill_edit",
            title=("Create skill " if create else "Edit skill ") + checked.name,
            policy="skill_create" if create else "skill_edit",
            reason="Skill instructions change what the agent does",
        )

    def propose_skill_delete(self, root: Path, name: str) -> ApprovalRecord:
        existing = Registry.build(root, None).find(name)
        if existing is None or existing.source != "workspace":
            raise ValueError("Only a skill installed in this workspace can be deleted")
        request = ApprovalRequest(
            approval_id="",
            run_id="",
            kind="tool",
            tool="skill_delete",
            path=f".harness/skills/{name}/SKILL.md",
            source_kind="configuration",
            source_title=f"Delete skill {name}",
            policy_code="skill_delete",
            reason="Deleting a skill removes files from the workspace",
            args={"remove": True, "name": name},
        )
        return self.propose(root, request)

    def propose_files(
        self,
        root: Path,
        name: str,
        files: dict[str, str],
        *,
        tool: str,
        title: str,
        policy: str,
        reason: str,
        extra: dict[str, str] | None = None,
    ) -> ApprovalRecord:
        if self.catalog.redactor.text("\n".join(files.values())) != "\n".join(files.values()):
            raise ValueError("Secret in the skill")
        return self.propose(
            root,
            ApprovalRequest(
                approval_id="",
                run_id="",
                kind="tool",
                tool=tool,
                path=f".harness/skills/{name}/SKILL.md",
                source_kind="configuration",
                source_title=title,
                policy_code=policy,
                reason=reason,
                args={"name": name, "files": cast(JsonValue, files), **(extra or {})},
            ),
        )

    def propose_mcp(
        self,
        root: Path,
        servers: list[McpServerConfig],
        *,
        tool: str,
        name: str,
        reason: str,
    ) -> ApprovalRecord:
        content = merged_mcp(servers)
        if self.catalog.redactor.text(content) != content:
            raise ValueError("Secret in the MCP configuration")
        return self.propose(
            root,
            ApprovalRequest(
                approval_id="",
                run_id="",
                kind="command",
                tool=tool,
                path=".harness/mcp.json",
                command=(servers[0].command[0] if servers and servers[0].command else None),
                source_kind="configuration",
                source_title=f"MCP server {name}",
                policy_code=tool,
                reason=reason,
                args={"content": content, "name": name},
            ),
        )

    def propose_agent_write(
        self, root: Path, value: AgentWriteInput, *, create: bool
    ) -> ApprovalRecord:
        existing = agents.read(root, value.name)
        if create and existing is not None:
            raise ValueError("That agent already exists")
        if not create and existing is None:
            raise ValueError("Unknown agent")
        content = agents.render(
            value.name, value.description, value.instructions, value.tools
        )
        parsed = agents.parse(content, value.name)
        if isinstance(parsed, str):
            raise ValueError(parsed)
        if self.catalog.redactor.text(content) != content:
            raise ValueError("Secret in the agent instructions")
        return self.propose(
            root,
            ApprovalRequest(
                approval_id="",
                run_id="",
                kind="tool",
                tool="agent_create" if create else "agent_edit",
                path=f".harness/agents/{value.name}.md",
                source_kind="configuration",
                source_title=("Create agent " if create else "Edit agent ") + value.name,
                policy_code="agent_create" if create else "agent_edit",
                reason="A workspace agent changes how delegated work is done",
                args={"name": value.name, "content": content},
            ),
        )

    def propose_agent_delete(self, root: Path, name: str) -> ApprovalRecord:
        if agents.read(root, name) is None:
            raise ValueError("Unknown agent")
        return self.propose(
            root,
            ApprovalRequest(
                approval_id="",
                run_id="",
                kind="tool",
                tool="agent_delete",
                path=f".harness/agents/{name}.md",
                source_kind="configuration",
                source_title=f"Delete agent {name}",
                policy_code="agent_delete",
                reason="Deleting an agent removes a file from the workspace",
                args={"remove": True, "name": name},
            ),
        )

    def propose_memory(self, root: Path, content: str) -> ApprovalRecord:
        if len(content.encode("utf-8")) > memory.LIMIT:
            raise ValueError(f"Memory is limited to {memory.LIMIT} bytes")
        if self.catalog.redactor.text(content) != content:
            raise ValueError("Secret in the memory file")
        return self.propose(
            root,
            ApprovalRequest(
                approval_id="",
                run_id="",
                kind="tool",
                tool="memory_update",
                path=".harness/memory.md",
                source_kind="configuration",
                source_title="Workspace memory",
                policy_code="memory_update",
                reason="Memory is read at the start of every run in this workspace",
                args={"content": content},
            ),
        )

    @serialized
    def propose(self, root: Path, request: ApprovalRequest) -> ApprovalRecord:
        request = ApprovalRequest.model_validate(
            self.catalog.redactor.value(request.model_dump(mode="json"))
        )
        select_workspace(self.catalog, str(root))
        identity = uuid4().hex
        request = prepare_review(
            root,
            request.model_copy(
                update={
                    "approval_id": identity,
                    "run_id": f"configuration-{identity}",
                    "workspace": str(root),
                }
            ),
        )
        ledger = ApprovalLedger(storage_path(root, "action-approvals.json"))
        request = ApprovalRequest.model_validate(
            self.catalog.redactor.value(request.model_dump(mode="json"))
        )
        return ledger.announce(request, request.run_id)

    @serialized
    def execution(
        self,
        run_id: str,
        approval_id: str,
        status: Literal["running", "completed", "interrupted"],
        result: str | None = None,
    ) -> None:
        ledger, record = self.find(run_id, approval_id)
        record.execution_status = status
        record.result = self.catalog.redactor.text(result) if result else None
        ledger.save()

    @serialized
    def resolve(self, run_id: str, approval_id: str, decision: ApprovalDecision) -> None:
        decision = ApprovalDecision.model_validate(
            self.catalog.redactor.value(decision.model_dump(mode="json"))
        )
        ledger, record = self.find(run_id, approval_id)
        if record.status != "pending":
            raise UnknownApproval(approval_id)
        request = record.request
        root = workspace_root(request.workspace)
        if decision.decision == "approve":
            if decision.edited_args is not None:
                raise ValueError("Edit the rules grid and submit a new proposal")
            current = prepare_review(root, request)
            if current.revision != request.revision:
                raise ValueError("Rules changed; submit a fresh proposal")
            if decision.revision and decision.revision != current.revision:
                raise ValueError("Review changed; refresh before approving")
            if request.tool in {"git_switch", "run_command"}:
                mode = request.args.get("mode")
                if mode is not None and mode not in {"ask", "auto", "read-only"}:
                    raise ValueError("Invalid permission mode")
                outcome = RulesEngine.load(root, cast(Mode | None, mode)).decide(
                    request.tool,
                    command=request.command,
                    timeout=float(str(request.args.get("timeout") or 120)),
                )
                if outcome.action == "deny":
                    raise ValueError("Current rules deny branch switching")
                record.execution_status = "running"
                ledger.answer(ApprovalAnswer(approval_id=approval_id, **decision.model_dump()))
                if request.tool == "run_command":
                    return
                result = switch(root, str(request.args["branch"]))
                if result.error:
                    record.execution_status = "interrupted"
                    record.result = self.catalog.redactor.text(result.error)
                    ledger.save()
                    raise ValueError("Git refused branch switching")
                record.execution_status = "completed"
                record.result = f"Branch: {result.branch}"
                ledger.save()
                return
            if request.tool == "worktree_create":
                ledger.answer(ApprovalAnswer(approval_id=approval_id, **decision.model_dump()))
                return
            if request.tool in {"skill_install", "skill_create", "skill_edit"}:
                files = request.args.get("files")
                name = str(request.args.get("name", ""))
                if not isinstance(files, dict) or not name:
                    raise ValueError("Invalid skill proposal")
                folder = self.skill_folder(root, name)
                manifest = {str(key): str(value) for key, value in files.items()}
                install.candidate(manifest)
                record.execution_status = "running"
                ledger.answer(ApprovalAnswer(approval_id=approval_id, **decision.model_dump()))
                try:
                    existing = folder / "SKILL.md"
                    if existing.is_file():
                        SnapshotStore(root, redactor=self.catalog.redactor).capture(
                            resolve_virtual(
                                root,
                                f".harness/skills/{name}/SKILL.md",
                                allow_protected=True,
                            ),
                            tool=request.tool,
                            call_id=approval_id,
                        )
                    install.write(folder, manifest)
                except (SnapshotError, OSError, ValueError):
                    record.execution_status = "interrupted"
                    record.result = (
                        "The skill was not written completely; inspect the folder before retrying."
                    )
                    ledger.save()
                    raise ValueError(record.result) from None
                record.execution_status = "completed"
                record.result = f"Skill {name} saved."
                ledger.save()
                return
            if request.tool == "skill_delete":
                name = str(request.args.get("name", ""))
                folder = self.skill_folder(root, name)
                ledger.answer(ApprovalAnswer(approval_id=approval_id, **decision.model_dump()))
                try:
                    if folder.is_dir():
                        shutil.rmtree(folder)
                except OSError:
                    record.execution_status = "interrupted"
                    record.result = "The skill folder could not be removed."
                    ledger.save()
                    raise ValueError(record.result) from None
                record.execution_status = "completed"
                record.result = f"Skill {name} deleted."
                ledger.save()
                return
            if request.tool in {"agent_create", "agent_edit"}:
                name = str(request.args.get("name", ""))
                content = str(request.args.get("content", ""))
                if not name or not content:
                    raise ValueError("Invalid agent proposal")
                parsed = agents.parse(content, name)
                if isinstance(parsed, str):
                    raise ValueError(parsed)
                record.execution_status = "running"
                ledger.answer(ApprovalAnswer(approval_id=approval_id, **decision.model_dump()))
                try:
                    target = agents.path_for(root, name)
                    if target.is_file():
                        SnapshotStore(root, redactor=self.catalog.redactor).capture(
                            resolve_virtual(
                                root, f".harness/agents/{name}.md", allow_protected=True
                            ),
                            tool=request.tool,
                            call_id=approval_id,
                        )
                    atomic_write(target, content)
                except (SnapshotError, OSError):
                    record.execution_status = "interrupted"
                    record.result = "The agent file was not written; inspect the folder."
                    ledger.save()
                    raise ValueError(record.result) from None
                record.execution_status = "completed"
                record.result = f"Agent {name} saved."
                ledger.save()
                return
            if request.tool == "agent_delete":
                name = str(request.args.get("name", ""))
                if not agents.NAME.match(name):
                    raise ValueError("Invalid agent name")
                ledger.answer(ApprovalAnswer(approval_id=approval_id, **decision.model_dump()))
                try:
                    agents.path_for(root, name).unlink(missing_ok=True)
                except OSError:
                    record.execution_status = "interrupted"
                    record.result = "The agent file could not be removed."
                    ledger.save()
                    raise ValueError(record.result) from None
                record.execution_status = "completed"
                record.result = f"Agent {name} deleted."
                ledger.save()
                return
            if request.tool == "memory_update":
                content = str(request.args.get("content", ""))
                record.execution_status = "running"
                ledger.answer(ApprovalAnswer(approval_id=approval_id, **decision.model_dump()))
                try:
                    SnapshotStore(root, redactor=self.catalog.redactor).capture(
                        resolve_virtual(root, ".harness/memory.md", allow_protected=True),
                        tool="memory_update",
                        call_id=approval_id,
                    )
                    atomic_write(memory.path_for(root), content)
                except (SnapshotError, OSError):
                    record.execution_status = "interrupted"
                    record.result = "Memory was not saved; inspect file permissions."
                    ledger.save()
                    raise ValueError(record.result) from None
                record.execution_status = "completed"
                record.result = "Memory saved."
                ledger.save()
                return
            remove = request.args.get("remove") is True
            config = request.tool in {
                "planning_settings_update",
                "verify_settings_update",
                "search_settings_update",
            }
            mcp = request.tool in {
                "mcp_server_add",
                "mcp_server_update",
                "mcp_server_delete",
            }
            if mcp:
                McpFile.model_validate_json(str(request.args["content"]))
            if not remove and not config and not mcp:
                RulesFile.model_validate_json(str(request.args["content"]))
            # An answer is durable before mutation. If the process dies in between,
            # the proposal stays decided and is never automatically applied again.
            record.execution_status = "running"
            ledger.answer(ApprovalAnswer(approval_id=approval_id, **decision.model_dump()))
            try:
                relative = (
                    ".harness/mcp.json"
                    if mcp
                    else ".harness/config.json"
                    if config
                    else ".harness/rules.json"
                )
                SnapshotStore(root, redactor=self.catalog.redactor).capture(
                    resolve_virtual(root, relative, allow_protected=True),
                    tool=request.tool if config or mcp else "rules_update",
                    call_id=approval_id,
                )
                target = storage_path(root, relative.rsplit("/", 1)[-1])
                if remove:
                    target.unlink(missing_ok=True)
                else:
                    atomic_write(target, str(request.args["content"]))
            except (SnapshotError, OSError):
                record.execution_status = "interrupted"
                record.result = "Settings were not saved; inspect credentials and file permissions."
                ledger.save()
                raise ValueError(record.result) from None
            record.execution_status = "completed"
            record.result = (
                "Planning settings saved."
                if request.tool == "planning_settings_update"
                else "Verification settings saved."
                if request.tool == "verify_settings_update"
                else "Search settings saved."
                if request.tool == "search_settings_update"
                else "MCP servers saved."
                if mcp
                else "Rules saved."
            )
            ledger.save()
        else:
            ledger.answer(ApprovalAnswer(approval_id=approval_id, **decision.model_dump()))
