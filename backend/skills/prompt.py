"""What a skill costs in the prompt, and what the prompt is allowed to say.

Only a name and a description reach the model. The body is a tool result, which is why a
hundred installed skills do not fill the window.
"""

from collections.abc import Iterable

from skills.types import SkillCommand, SkillRecord

MAX_BLOCK = 2_000
MAX_LINE_DESCRIPTION = 160
MAX_MEMORY = 4_000
CHARS_PER_TOKEN = 4

HEADING = "Skills (call load_skill with a name to read its full instructions):"

ACTIVATION_PREFIX = "[harness] "
ACTIVATION_SEPARATOR = "\n\n---\n\n"
"""A slash command puts the body before the person's words, behind this separator."""


def activation_message(command: str, name: str, body: str, task: str) -> str:
    """The first human turn when a slash command named a skill."""
    return (
        f"{ACTIVATION_PREFIX}{command} activated the {name} skill. "
        f"Follow it for this task.\n\n{body}{ACTIVATION_SEPARATOR}{task}"
    )


def task_of(message: str) -> str:
    """The person's own words, with any activation envelope removed."""
    if message.startswith(ACTIVATION_PREFIX):
        return message.rsplit(ACTIVATION_SEPARATOR, 1)[-1]
    return message


def estimate_tokens(text: str) -> int:
    """A stable approximation, marked with `~` wherever it is shown."""
    return max(1, (len(text) + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN)


def summary_line(name: str, description: str) -> str:
    text = " ".join(description.split())
    if len(text) > MAX_LINE_DESCRIPTION:
        text = text[: MAX_LINE_DESCRIPTION - 1].rstrip() + "…"
    return f"- {name}: {text}"


def skills_block(skills: Iterable[SkillRecord]) -> str:
    """The bounded block: enabled, unbroken skills only, name and description only."""
    lines = [HEADING]
    for skill in sorted(skills, key=lambda item: item.name):
        if not skill.enabled or skill.problem:
            continue
        line = summary_line(skill.name, skill.description)
        if sum(len(item) + 1 for item in lines) + len(line) > MAX_BLOCK:
            lines.append("…")
            break
        lines.append(line)
    return "\n".join(lines) if len(lines) > 1 else ""


def memory_block(content: str) -> str:
    """The person's memory file, bounded and never a place for secrets."""
    text = content.strip()
    if not text:
        return ""
    if len(text) > MAX_MEMORY:
        text = text[:MAX_MEMORY].rstrip() + "\n…"
    return (
        "Workspace memory (written by the person, follow it unless it conflicts "
        f"with a request):\n{text}"
    )


def commands(skills: Iterable[SkillRecord]) -> list[SkillCommand]:
    """Enabled skills that declare a slash command, one per command."""
    found: dict[str, SkillCommand] = {}
    for skill in sorted(skills, key=lambda item: item.name):
        if not skill.enabled or skill.problem or not skill.command:
            continue
        if skill.command in found:
            # Two skills claiming one command is a conflict, not a merge: the first
            # name in sort order wins and the hub still lists both skills.
            continue
        found[skill.command] = SkillCommand(
            command=skill.command,
            name=skill.name,
            description=skill.description,
            requires_approval=skill.requires_approval,
        )
    return sorted(found.values(), key=lambda item: item.command)


def activated(command: str, skills: Iterable[SkillRecord]) -> SkillRecord | None:
    return next(
        (
            skill
            for skill in skills
            if skill.enabled and not skill.problem and skill.command == command
        ),
        None,
    )
