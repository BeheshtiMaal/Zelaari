"""Pre-use security scan: list the scripts, name the risky patterns, block two of them.

The scan is not a sandbox and does not claim to be one. It answers one question a person
about to switch a skill on actually asks: what does this folder contain, and does it ask
the shell to do something destructive or opaque? `blocked` exists for the two patterns
that are never acceptable in a skill.
"""

import os
import re
from pathlib import Path

from skills.types import ScanStatus, SkillScan

MAX_SCRIPTS = 50
MAX_SCRIPT_BYTES = 64_000
MAX_DEPTH = 3

BLOCKING = frozenset({"rm_rf", "pipe_to_shell"})

PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "rm_rf",
        re.compile(
            r"rm\s+-[a-z]*r[a-z]*f[a-z]*\s|rm\s+-[a-z]*f[a-z]*r[a-z]*\s"
            r"|Remove-Item[^\n]*-Recurse[^\n]*-Force|rd\s+/s\s+/q",
            re.IGNORECASE,
        ),
    ),
    (
        "pipe_to_shell",
        re.compile(
            r"(curl|wget|Invoke-WebRequest|iwr)\b[^\n|]*\|\s*(sh|bash|zsh|powershell|pwsh|iex|Invoke-Expression)",
            re.IGNORECASE,
        ),
    ),
    ("invoke_expression", re.compile(r"Invoke-Expression|\biex\b", re.IGNORECASE)),
    ("eval", re.compile(r"\beval\s*\(|\bexec\s*\(", re.IGNORECASE)),
    (
        "base64_decode",
        re.compile(r"base64\s+(-d|--decode)|FromBase64String", re.IGNORECASE),
    ),
    ("sudo", re.compile(r"\bsudo\b|Start-Process[^\n]*-Verb\s+RunAs", re.IGNORECASE)),
    ("chmod_777", re.compile(r"chmod\s+(-R\s+)?777", re.IGNORECASE)),
    (
        "execution_policy",
        re.compile(r"Set-ExecutionPolicy[^\n]*Bypass|ExecutionPolicy\s+Bypass", re.IGNORECASE),
    ),
    (
        "absolute_path",
        re.compile(
            r"(^|[\s\"'`])/(usr|etc|home|var|bin|opt|tmp)/|[A-Za-z]:\\\\?[A-Za-z0-9_.-]",
            re.IGNORECASE,
        ),
    ),
    (
        "net_upload",
        re.compile(
            r"curl[^\n]*(\s-d\s|\s--data|\s-F\s|\s--form|\s-T\s|\s--upload-file)"
            r"|\bscp\b|\brsync\b[^\n]*:",
            re.IGNORECASE,
        ),
    ),
)

LABELS = {
    "rm_rf": "deletes files recursively",
    "pipe_to_shell": "pipes a download into a shell",
    "invoke_expression": "evaluates a string as code",
    "eval": "evaluates dynamic code",
    "base64_decode": "decodes an opaque payload",
    "sudo": "asks for elevated privileges",
    "chmod_777": "makes files world-writable",
    "execution_policy": "disables the script execution policy",
    "absolute_path": "touches a path outside the workspace",
    "net_upload": "uploads data to a remote host",
}


def is_link(path: Path) -> bool:
    try:
        return path.is_symlink() or path.is_junction()
    except OSError:
        return True


def scripts(folder: Path) -> list[str]:
    """Relative paths under `scripts/`, bounded and never through a link."""
    base = folder / "scripts"
    if is_link(base) or not base.is_dir():
        return []
    found: list[str] = []
    for current, directories, files in os.walk(base, followlinks=False):
        root = Path(current)
        depth = len(root.relative_to(base).parts)
        directories[:] = [
            name for name in sorted(directories) if depth < MAX_DEPTH and not is_link(root / name)
        ]
        for name in sorted(files):
            path = root / name
            if is_link(path) or not path.is_file():
                continue
            found.append(path.relative_to(folder).as_posix())
            if len(found) >= MAX_SCRIPTS:
                return found
    return found


def read_bounded(path: Path) -> str:
    try:
        with path.open("rb") as handle:
            raw = handle.read(MAX_SCRIPT_BYTES)
    except OSError:
        return ""
    return raw.decode("utf-8", errors="replace")


def findings_in(text: str) -> set[str]:
    return {identifier for identifier, pattern in PATTERNS if pattern.search(text)}


def scan_text(*texts: str) -> set[str]:
    found: set[str] = set()
    for text in texts:
        found |= findings_in(text)
    return found


def scan_skill(folder: Path, body: str) -> SkillScan:
    """Scan the body and every script; `blocked` outranks `flagged`."""
    listed = scripts(folder)
    texts = [body, *(read_bounded(folder / name) for name in listed)]
    found = scan_text(*texts)
    status: ScanStatus = "blocked" if found & BLOCKING else "flagged" if found else "clean"
    return SkillScan(status=status, findings=sorted(found), scripts=listed)


def describe(scan: SkillScan) -> str:
    """One line for a tool result or an approval reason."""
    if scan.status == "clean":
        return "security scan: no risky patterns"
    labels = ", ".join(LABELS.get(item, item) for item in scan.findings)
    return f"security scan: {scan.status} ({labels})"
