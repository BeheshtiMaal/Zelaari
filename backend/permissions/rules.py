"""Rules grid: tool x path glob -> allow/ask/deny, plus the mode ceiling and always-ask list."""

import fnmatch
import json
from pathlib import Path
from typing import Literal

from permissions.classifier import assess
from permissions.types import Action, Mode, PermissionOutcome, RiskAssessment, Rule, RulesFile
from tools.atomic import atomic_write
from tools.jail import storage_path

READ_TOOLS = frozenset({"ls", "read_file", "glob", "grep"})
WRITE_TOOLS = frozenset({"write_file", "edit_file"})
DELETE_TOOLS = frozenset({"delete"})
COMMAND_TOOLS = frozenset({"run_command", "git_switch", "worktree_create"})
WEB_TOOLS = frozenset({"web_search"})

Category = Literal["read", "write", "delete", "command", "web"]

DEFAULTS: dict[Mode, dict[Category, Action]] = {
    "read-only": {
        "read": "allow",
        "write": "deny",
        "delete": "deny",
        "command": "deny",
        "web": "deny",
    },
    "ask": {
        "read": "allow",
        "write": "ask",
        "delete": "ask",
        "command": "ask",
        "web": "ask",
    },
    "auto": {
        "read": "allow",
        "write": "allow",
        "delete": "allow",
        "command": "allow",
        "web": "ask",
    },
}

RANK: dict[Action, int] = {"allow": 0, "ask": 1, "deny": 2}


def category_of(tool: str) -> Category:
    if tool in READ_TOOLS:
        return "read"
    if tool in WRITE_TOOLS:
        return "write"
    if tool in DELETE_TOOLS:
        return "delete"
    if tool in WEB_TOOLS:
        return "web"
    return "command"


def _specificity(glob: str) -> tuple[int, int]:
    wildcard = glob.find("*")
    literal = len(glob) if wildcard < 0 else wildcard
    return literal, -glob.count("*")


class RulesEngine:
    """One instance per run. Never trusts the workspace to be well-formed."""

    def __init__(
        self,
        root: Path,
        mode: Mode = "ask",
        rules: RulesFile | None = None,
        *,
        load_error: str | None = None,
    ) -> None:
        self.root = root
        self.mode: Mode = mode
        self.rules = rules or RulesFile(mode=mode)
        self.load_error = load_error

    # -- loading -----------------------------------------------------------
    @classmethod
    def load(cls, root: Path, mode: Mode | None = None) -> "RulesEngine":
        path = storage_path(root, "rules.json")
        if not path.is_file():
            return cls(root, mode or "ask")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            rules = RulesFile.model_validate(data)
        except (OSError, ValueError) as error:
            # Fail closed: an unreadable grid must not silently allow anything.
            return cls(root, mode or "ask", load_error=f"rules.json is unreadable: {error}")
        return cls(root, mode or rules.mode, rules)

    def save(self, rules: RulesFile) -> None:
        target = storage_path(self.root, "rules.json")
        atomic_write(target, rules.model_dump_json(indent=2))
        self.rules = rules

    # -- decisions ---------------------------------------------------------
    def _explicit(self, tool: str, path: str | None) -> Rule | None:
        candidates = self.rules.tools.get(tool) or []
        if not candidates:
            return None
        if path is None:
            matching = [rule for rule in candidates if rule.glob == "*"]
        else:
            probe = path.replace("\\", "/").lower()
            matching = [rule for rule in candidates if fnmatch.fnmatch(probe, rule.glob.lower())]
        if not matching:
            return None
        matching.sort(key=lambda rule: (*_specificity(rule.glob), RANK[rule.action]), reverse=True)
        return matching[0]

    def _always_ask(self, tool: str, path: str | None, command: str | None) -> str | None:
        if path is not None and path.replace("\\", "/").split("/")[0].casefold() == ".harness":
            return "engine storage always needs approval"
        if tool in WEB_TOOLS:
            return "every web query needs approval"
        if command is not None:
            risk = assess(command, self.root)
            if risk.level == "high":
                return risk.reasons[0] if risk.reasons else "high-risk command"
        return None

    def decide(
        self,
        tool: str,
        *,
        path: str | None = None,
        command: str | None = None,
    ) -> PermissionOutcome:
        category = category_of(tool)
        ceiling = DEFAULTS[self.mode][category]
        risk = assess(command, self.root) if command is not None else None

        if self.load_error:
            return PermissionOutcome(
                action="ask" if ceiling != "deny" else "deny",
                reason=self.load_error,
                risk=risk or RiskAssessment(),
            )

        if ceiling == "deny":
            return PermissionOutcome(
                action="deny",
                reason=f"{self.mode} mode blocks {category}",
                risk=risk or RiskAssessment(),
            )

        explicit = self._explicit(tool, path)
        action: Action = explicit.action if explicit else DEFAULTS[self.mode][category]
        reason = (
            f"rule {explicit.glob} for {tool}"
            if explicit
            else f"default {category} policy in {self.mode} mode"
        )

        if action == "allow":
            # An explicit allow rule is the documented escape hatch from always-ask.
            if explicit is None:
                escalation = self._always_ask(tool, path, command)
                if escalation:
                    action, reason = "ask", escalation
        elif action == "ask":
            escalation = self._always_ask(tool, path, command)
            if escalation and escalation != reason:
                reason = f"{reason}; {escalation}"

        return PermissionOutcome(action=action, reason=reason, risk=risk or RiskAssessment())

    # -- introspection -----------------------------------------------------
    def always_ask(self) -> list[str]:
        return [
            ".harness/ writes",
            "web_search queries",
            "high-risk commands",
            "timeouts above the default",
        ]
