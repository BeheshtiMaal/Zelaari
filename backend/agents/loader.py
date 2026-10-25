"""`.harness/agents/<name>.md`: one frontmatter block and the agent's instructions.

The folder is engine storage, so a write is a protected-configuration change like any
other. Reading is bounded and never follows a link: a name maps to exactly one file.
"""

import re
from pathlib import Path

from agents import tools
from skills import frontmatter
from skills.types import AgentDocument, AgentRecord
from tools.jail import storage_path

NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")
KEYS = {"name", "description", "tools"}
MAX_AGENTS = 32
MAX_FILE_BYTES = 64_000
MAX_INSTRUCTIONS = 32_000
MAX_DESCRIPTION = 512


def folder(root: Path) -> Path:
    return storage_path(root, "agents")


def path_for(root: Path, name: str) -> Path:
    return storage_path(root, f"agents/{name}.md")


def parse(text: str, name: str) -> tuple[AgentRecord, str] | str:
    """A record and its instructions, or one sentence explaining what is wrong."""
    parsed = frontmatter.split(text, keys=KEYS, label=f"{name}.md")
    if parsed.problem:
        return parsed.problem
    declared = parsed.meta.get("name")
    if not isinstance(declared, str) or not NAME.match(declared):
        return "name must be lowercase letters, digits or dashes (max 32)"
    if declared != name:
        return f"file name `{name}.md` does not match agent name `{declared}`"
    description = parsed.meta.get("description")
    if not isinstance(description, str) or not description.strip():
        return "description is required"
    description = " ".join(description.split())
    if len(description) > MAX_DESCRIPTION:
        return f"description is longer than {MAX_DESCRIPTION} characters"
    raw = parsed.meta.get("tools", "")
    if not isinstance(raw, str):
        return "tools must be a comma-separated list"
    requested = [item for item in raw.split(",")]
    body = parsed.body
    if not body.strip():
        return "instructions are required"
    if len(body) > MAX_INSTRUCTIONS:
        return f"instructions are longer than {MAX_INSTRUCTIONS} characters"
    return (
        AgentRecord(
            name=declared,
            description=description,
            tools=tools.allowed(requested),
            path=f".harness/agents/{name}.md",
        ),
        body,
    )


def read(root: Path, name: str) -> AgentDocument | None:
    if not NAME.match(name):
        return None
    path = path_for(root, name)
    try:
        if not path.is_file() or path.is_symlink():
            return None
        if path.stat().st_size > MAX_FILE_BYTES:
            return AgentDocument(
                record=AgentRecord(name=name, description="", problem="File is too large")
            )
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return AgentDocument(
            record=AgentRecord(name=name, description="", problem="File cannot be read")
        )
    parsed = parse(text, name)
    if isinstance(parsed, str):
        return AgentDocument(record=AgentRecord(name=name, description="", problem=parsed))
    record, instructions = parsed
    return AgentDocument(record=record, instructions=instructions)


def discover(root: Path) -> list[AgentRecord]:
    """Every readable agent, in name order; a broken file is a card with a problem."""
    base = folder(root)
    try:
        if not base.is_dir():
            return []
        entries = sorted(
            (item for item in base.iterdir() if item.suffix == ".md" and item.is_file()),
            key=lambda item: item.stem,
        )
    except OSError:
        return []
    found: list[AgentRecord] = []
    for entry in entries[:MAX_AGENTS]:
        if entry.is_symlink():
            continue
        document = read(root, entry.stem)
        if document is None:
            continue
        record = document.record
        if record.problem is None and not document.instructions.strip():
            record = record.model_copy(update={"problem": "instructions are required"})
        found.append(record)
    return found


def render(name: str, description: str, instructions: str, names: list[str]) -> str:
    lines = ["---", f"name: {name}", f"description: {description}"]
    chosen = tools.allowed(names)
    if chosen:
        lines.append(f"tools: {', '.join(chosen)}")
    lines.append("---")
    return "\n".join([*lines, "", instructions.strip("\n"), ""])
