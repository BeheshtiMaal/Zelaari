"""Discovery in three roots, with the nearest folder winning.

Bundled skills are part of the product; user skills belong to the person; workspace skills
belong to one project. A name in a nearer root replaces the farther one, so a project can
pin its own version without touching the installation.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from skills import frontmatter
from skills.prompt import estimate_tokens, summary_line
from skills.scan import is_link, scan_skill
from skills.types import SkillCategory, SkillDetail, SkillRecord, SkillSource, SkillsState

SKILL_FILE = "SKILL.md"
MAX_SKILLS_PER_ROOT = 200
MAX_SKILL_BYTES = 64_000
BUNDLED_ENV = "CODEHARNESS_BUNDLED_SKILLS"


@dataclass(frozen=True)
class Root:
    path: Path
    source: SkillSource
    prefix: str


def bundled_root() -> Path:
    override = os.environ.get(BUNDLED_ENV)
    if override:
        return Path(override)
    # backend/skills/loader.py -> repository root
    return Path(__file__).resolve().parents[2] / "skills"


def roots(workspace: Path | None, app_data: Path | None) -> list[Root]:
    found = [Root(bundled_root(), "bundled", "skills")]
    if app_data is not None:
        found.append(Root(app_data / "skills", "user", "user/skills"))
    if workspace is not None:
        found.append(Root(workspace / ".harness" / "skills", "workspace", ".harness/skills"))
    return found


def read_text(path: Path, limit: int = MAX_SKILL_BYTES) -> str:
    try:
        with path.open("rb") as handle:
            raw = handle.read(limit + 1)
    except OSError:
        return ""
    return raw[:limit].decode("utf-8", errors="replace")


def read_record(folder: Path, root: Root, state: SkillsState) -> SkillRecord:
    """One folder -> one record. A broken folder stays listed with its reason."""
    name = folder.name
    display = f"{root.prefix}/{name}"
    path = folder / SKILL_FILE
    if is_link(path) or not path.is_file():
        return SkillRecord(
            name=name,
            description="",
            source=root.source,
            path=display,
            enabled=False,
            problem=f"{SKILL_FILE} is missing",
        )
    text = read_text(path)
    fields, problem = frontmatter.validate(frontmatter.split(text), name)
    if problem:
        return SkillRecord(
            name=name,
            description="",
            source=root.source,
            path=display,
            enabled=False,
            problem=problem,
        )
    scan = scan_skill(folder, str(fields["body"]))
    category = str(fields["category"])
    record = SkillRecord(
        name=str(fields["name"]),
        description=str(fields["description"]),
        command=str(fields["command"]) if fields["command"] else None,
        category=cast(SkillCategory, category),
        source=root.source,
        path=display,
        enabled=bool(fields["enabled"]),
        requires_approval=bool(fields["requires_approval"]),
        tokens=estimate_tokens(summary_line(str(fields["name"]), str(fields["description"]))),
        scan=scan,
    )
    return record.model_copy(update={"enabled": state.overrides.get(name, record.enabled)})


def folders(root: Root) -> list[Path]:
    if is_link(root.path) or not root.path.is_dir():
        return []
    try:
        entries = sorted(os.scandir(root.path), key=lambda item: item.name)
    except OSError:
        return []
    found: list[Path] = []
    for entry in entries:
        if len(found) >= MAX_SKILLS_PER_ROOT:
            break
        try:
            if not entry.is_dir(follow_symlinks=False):
                continue
        except OSError:
            continue
        path = Path(entry.path)
        if is_link(path):
            continue
        found.append(path)
    return found


def discover(
    workspace: Path | None,
    app_data: Path | None = None,
    state: SkillsState | None = None,
) -> list[SkillRecord]:
    """All skills, nearest root last so it wins; sorted by name for a stable UI."""
    switches = state or SkillsState()
    merged: dict[str, SkillRecord] = {}
    for root in roots(workspace, app_data):
        for folder in folders(root):
            record = read_record(folder, root, switches)
            merged[record.name] = record
    return sorted(merged.values(), key=lambda record: record.name)


def find(records: list[SkillRecord], name: str) -> SkillRecord | None:
    return next((record for record in records if record.name == name), None)


def detail(record: SkillRecord, workspace: Path | None, app_data: Path | None) -> SkillDetail:
    """The body, re-read and re-scanned: an edited skill cannot keep an old verdict."""
    root = next(
        (item for item in roots(workspace, app_data) if item.source == record.source), None
    )
    if root is None:
        return SkillDetail(**record.model_dump())
    folder = root.path / record.name
    text = read_text(folder / SKILL_FILE)
    parsed = frontmatter.split(text)
    scan = scan_skill(folder, parsed.body)
    references: list[str] = []
    reference_dir = folder / "references"
    if reference_dir.is_dir() and not is_link(reference_dir):
        references = sorted(
            path.name
            for path in reference_dir.glob("*")
            if path.is_file() and not is_link(path)
        )
    fields = record.model_dump()
    fields["scan"] = scan.model_dump()
    return SkillDetail(
        **fields,
        body=parsed.body[: frontmatter.MAX_BODY],
        references=references,
    )


def install_folder(
    workspace: Path | None, app_data: Path | None, source: SkillSource
) -> Path | None:
    """Where a skill of that source is written. Bundled content is never mutated."""
    root = next(
        (item for item in roots(workspace, app_data) if item.source == source), None
    )
    return root.path if root else None
