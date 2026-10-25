"""The bounded frontmatter subset a `SKILL.md` may use.

No YAML parser: a skill file is configuration a person reads, so the accepted shape is
small enough to parse exactly and to explain in one error message. Anything outside it is
a `problem` on the record, never an exception.
"""

import re
from dataclasses import dataclass, field
from typing import Literal

NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
COMMAND = re.compile(r"^/[a-z0-9-]{1,32}$")
KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$")
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

MAX_DESCRIPTION = 1024
MAX_BODY = 32_000
MAX_FRONTMATTER_LINES = 80
ALLOWED = {"name", "description", "command", "category", "requires_approval", "enabled"}
CATEGORIES = {"coding", "tests", "web", "docs", "other"}
BOOLEAN = {"requires_approval", "enabled"}

Category = Literal["coding", "tests", "web", "docs", "other"]


@dataclass(frozen=True)
class Parsed:
    meta: dict[str, str | bool] = field(default_factory=dict)
    body: str = ""
    problem: str | None = None


def _scalar(value: str, key: str) -> str | bool:
    """Only the two boolean keys coerce; a skill may legitimately be called `off`."""
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        return text[1:-1]
    if key in BOOLEAN:
        lowered = text.casefold()
        if lowered in {"true", "yes", "on"}:
            return True
        if lowered in {"false", "no", "off"}:
            return False
    return text


def split(text: str, *, keys: set[str] | None = None, label: str = "SKILL.md") -> Parsed:
    """Split `---` frontmatter from the body; keep reading even when it is malformed.

    `keys` and `label` let a `.harness/agents/<name>.md` file reuse this parser with its
    own small vocabulary and its own name in the error message.
    """
    allowed = ALLOWED if keys is None else keys
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.startswith("---"):
        return Parsed(problem=f"{label} must start with a --- frontmatter block")
    lines = normalized.split("\n")
    closing = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"), None
    )
    if closing is None:
        return Parsed(problem=f"{label} frontmatter is not closed")
    if closing > MAX_FRONTMATTER_LINES:
        return Parsed(problem=f"{label} frontmatter is too long")

    meta: dict[str, str | bool] = {}
    current: str | None = None
    for raw in lines[1:closing]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw[:1] in {" ", "\t"}:
            if current is None:
                return Parsed(problem=f"{label} frontmatter has a stray continuation line")
            previous = meta[current]
            joined = f"{previous} {raw.strip()}".strip()
            meta[current] = joined if isinstance(previous, str) else previous
            continue
        match = KEY.match(raw)
        if match is None:
            return Parsed(problem=f"{label} frontmatter line is not `key: value`: {raw[:40]}")
        key, value = match.group(1), match.group(2)
        if key not in allowed:
            return Parsed(problem=f"Unknown frontmatter key: {key}")
        if key in meta:
            return Parsed(problem=f"Duplicate frontmatter key: {key}")
        meta[key] = _scalar(value, key)
        current = key
    body = "\n".join(lines[closing + 1 :]).strip("\n")
    return Parsed(meta=meta, body=body)


def validate(parsed: Parsed, folder: str) -> tuple[dict[str, object], str | None]:
    """Turn parsed frontmatter into record fields, or explain why it is unusable."""
    if parsed.problem:
        return {}, parsed.problem
    meta = parsed.meta
    name = meta.get("name")
    if not isinstance(name, str) or not NAME.match(name):
        return {}, "name must be lowercase letters, digits or dashes (max 64)"
    if name != folder:
        return {}, f"folder name `{folder}` does not match skill name `{name}`"
    description = meta.get("description")
    if not isinstance(description, str) or not description.strip():
        return {}, "description is required"
    description = " ".join(description.split())
    if len(description) > MAX_DESCRIPTION:
        return {}, f"description is longer than {MAX_DESCRIPTION} characters"
    if CONTROL.search(description):
        return {}, "description contains control characters"
    command = meta.get("command")
    if command is not None and (not isinstance(command, str) or not COMMAND.match(command)):
        return {}, "command must look like /name"
    category = meta.get("category", "other")
    if not isinstance(category, str) or category not in CATEGORIES:
        return {}, "category must be coding, tests, web, docs or other"
    for key in BOOLEAN:
        if key in meta and not isinstance(meta[key], bool):
            return {}, f"{key} must be true or false"
    if len(parsed.body) > MAX_BODY:
        return {}, f"body is longer than {MAX_BODY} characters"
    return (
        {
            "name": name,
            "description": description,
            "command": command,
            "category": category,
            "requires_approval": bool(meta.get("requires_approval", False)),
            "enabled": bool(meta.get("enabled", True)),
            "body": parsed.body,
        },
        None,
    )


def render(meta: dict[str, object], body: str) -> str:
    """Serialize a skill back to `SKILL.md` (used by create, edit and install)."""
    lines = ["---", f"name: {meta['name']}", f"description: {meta['description']}"]
    if meta.get("command"):
        lines.append(f"command: {meta['command']}")
    category = str(meta.get("category") or "other")
    if category != "other":
        lines.append(f"category: {category}")
    if meta.get("requires_approval"):
        lines.append("requires_approval: true")
    if meta.get("enabled") is False:
        lines.append("enabled: false")
    lines.append("---")
    return "\n".join([*lines, "", body.strip("\n"), ""])
