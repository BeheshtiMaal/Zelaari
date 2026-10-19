"""Table-driven command risk classification.

Patterns run against a normalised command so quoting, chaining and PowerShell aliases
cannot hide intent. A false negative on a listed category fails the phase, so the
table is deliberately blunt: it prefers a false positive over a missed delete.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from permissions.types import RiskAssessment
from tools.jail import JailError, resolve

# PowerShell aliases that stand in for a cmdlet we check by name.
ALIASES = {
    "ri": "remove-item",
    "rm": "remove-item",
    "del": "remove-item",
    "erase": "remove-item",
    "rd": "remove-item",
    "rmdir": "remove-item",
    "gci": "get-childitem",
    "iwr": "invoke-webrequest",
    "irm": "invoke-restmethod",
    "iex": "invoke-expression",
    "curl": "invoke-webrequest",
    "wget": "invoke-webrequest",
}

_SEPARATORS = re.compile(r"(?:&&|\|\||[;|\n\r])")
_QUOTES = re.compile(r"[\"']")
_DELETE_FLAGS = r"(-recurse|-force|/s\b|/q\b|/f\b|-[a-z]*[rf]\b)"

_PATH_TOKEN = re.compile(
    r"[a-z]:[\\/][^\s\"'|;&]*|\\\\[^\s\"'|;&]+|(?:[^\s\"'|;&]*\.\.[^\s\"'|;&]*)"
)


@dataclass(frozen=True)
class Rule:
    category: str
    reason: str
    pattern: re.Pattern[str]


def _rule(category: str, reason: str, pattern: str) -> Rule:
    return Rule(category, reason, re.compile(pattern, re.I))


TABLE: tuple[Rule, ...] = (
    _rule(
        "recursive-delete",
        "recursive or forced delete",
        rf"\bremove-item\b.*{_DELETE_FLAGS}"
        rf"|\b(rm|del|erase|rd|rmdir)\b.*{_DELETE_FLAGS}"
        r"|\b(get-childitem|gci)\b.*\|\s*remove-item",
    ),
    _rule(
        "disk",
        "disk or volume operation",
        r"\b(format|diskpart|mkfs|fdisk|shutdown|clear-disk|initialize-disk|format-volume)\b",
    ),
    _rule(
        "registry",
        "registry modification",
        r"\breg(\.exe)?\s+(add|delete|import|restore)\b"
        r"|\b(set|new|remove)-itemproperty\b.*\b(hklm|hkcu|hkey_)"
        r"|\bregedit\b",
    ),
    _rule(
        "encoded-powershell",
        "encoded or obfuscated command",
        r"-e(nc|ncodedcommand)?\s+[a-z0-9+/=]{16,}|frombase64string|-w(indowstyle)?\s+hidden",
    ),
    _rule(
        "pipe-to-shell",
        "download piped into a shell",
        r"(curl|wget|invoke-webrequest|invoke-restmethod|iwr|irm)\b.*\|\s*"
        r"(sh|bash|zsh|iex|invoke-expression|powershell|pwsh|python)",
    ),
    _rule(
        "git-force-push",
        "force push rewrites remote history",
        r"\bgit\s+push\b.*(--force\b|\s-f\b)",
    ),
    _rule("git-reset-hard", "hard reset discards local work", r"\bgit\s+reset\s+--hard\b"),
    _rule("git-clean", "clean deletes untracked files", r"\bgit\s+clean\b.*-[a-z]*f"),
    _rule(
        "package-install",
        "package install or uninstall changes dependencies",
        r"\b(npm|pnpm|yarn)\s+(install|i|add|remove|uninstall|upgrade|update)\b"
        r"|\b(pip|pip3)\s+(install|uninstall)\b"
        r"|\buv\s+(pip\s+)?(install|add|remove|sync)\b"
        r"|\b(winget|choco|scoop)\s+(install|uninstall|upgrade)\b"
        r"|\bapt(-get)?\s+(install|remove|purge)\b",
    ),
    _rule(
        "network",
        "network access",
        r"\b(curl|wget|nc|ncat|netcat|telnet|ssh|scp|sftp|ftp"
        r"|invoke-webrequest|invoke-restmethod|iwr|irm)\b",
    ),
)


def normalise(command: str) -> str:
    """Lowercase, drop quotes and expand aliases, keeping segment structure."""
    text = _QUOTES.sub("", command.lower())
    segments: list[str] = []
    for segment in _SEPARATORS.split(text):
        tokens = segment.strip().split()
        if tokens and tokens[0] in ALIASES:
            tokens[0] = ALIASES[tokens[0]]
        segments.append(" ".join(tokens))
    return " ; ".join(part for part in segments if part)


def _path_reasons(text: str, root: Path | None) -> list[str]:
    reasons: list[str] = []
    for token in _PATH_TOKEN.findall(text):
        candidate = token.strip().rstrip(",;")
        if not candidate:
            continue
        if root is None:
            reason = "absolute path outside the workspace"
            if reason not in reasons:
                reasons.append(reason)
            continue
        try:
            resolved = resolve(root, candidate, allow_protected=True)
        except JailError:
            if "absolute path outside the workspace" not in reasons:
                reasons.append("absolute path outside the workspace")
            continue
        if resolved.is_protected and "engine storage" not in reasons:
            reasons.append("engine storage")
    return reasons


def assess(command: str, root: Path | None = None) -> RiskAssessment:
    text = normalise(command)
    raw = command.lower()
    reasons: list[str] = []
    for rule in TABLE:
        # Check both shapes: the segmented form catches alias/chained intent, the raw
        # form keeps pipe operators visible for pipe-to-shell and gci|remove-item.
        if (rule.pattern.search(text) or rule.pattern.search(raw)) and rule.reason not in reasons:
            reasons.append(rule.reason)
    for reason in _path_reasons(text, root):
        if reason not in reasons:
            reasons.append(reason)
    return RiskAssessment(level="high" if reasons else "low", reasons=reasons)
