"""Turn a folder, a ZIP or a Git URL into a validated, scanned, text-only manifest.

Nothing is written here. An install becomes a proposal with exact bytes; the approval
ledger is the only writer, so a refused install cannot leave half a skill behind.
"""

import shutil
import stat
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import cast
from urllib.parse import urlparse

from skills import frontmatter
from skills.scan import BLOCKING, scan_text
from skills.types import ScanStatus, SkillScan

MAX_FILES = 200
MAX_FILE_BYTES = 64_000
MAX_TOTAL_BYTES = 1_000_000
MAX_ZIP_BYTES = 8_000_000
ALLOWED_ROOTS = {"SKILL.md"}
ALLOWED_PREFIXES = ("scripts/", "references/")
GIT_TIMEOUT = 60.0


@dataclass(frozen=True)
class Candidate:
    name: str
    files: dict[str, str]
    scan: SkillScan


def safe_name(value: str) -> str:
    """A workspace-relative POSIX path inside a skill folder, or a refusal."""
    text = value.replace("\\", "/")
    if text.startswith("/"):
        raise ValueError("The skill contains an absolute path")
    text = text.strip("/")
    path = PurePosixPath(text)
    if not text or path.is_absolute() or any(part in {"..", ""} for part in path.parts):
        raise ValueError("The skill contains an unsafe path")
    if ":" in text:
        raise ValueError("The skill contains an unsafe path")
    return path.as_posix()


def allowed(relative: str) -> bool:
    return relative in ALLOWED_ROOTS or relative.startswith(ALLOWED_PREFIXES)


def read_text(path: Path) -> str:
    raw = path.read_bytes()
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError(f"{path.name} is larger than {MAX_FILE_BYTES} bytes")
    try:
        return raw.decode("utf-8")
    except UnicodeError:
        raise ValueError("Skills may only contain text files") from None


def from_folder(path: Path) -> dict[str, str]:
    if not path.is_dir():
        raise ValueError("That folder does not exist")
    files: dict[str, str] = {}
    total = 0
    for item in sorted(path.rglob("*"), key=str):
        if item.is_dir():
            continue
        if item.is_symlink():
            continue
        relative = safe_name(str(item.relative_to(path)))
        if not allowed(relative):
            continue
        if len(files) >= MAX_FILES:
            raise ValueError(f"A skill is limited to {MAX_FILES} files")
        text = read_text(item)
        total += len(text.encode())
        if total > MAX_TOTAL_BYTES:
            raise ValueError("The skill is too large")
        files[relative] = text
    return files


def from_zip(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise ValueError("That ZIP file does not exist")
    if path.stat().st_size > MAX_ZIP_BYTES:
        raise ValueError("The ZIP file is larger than 8 MB")
    collected: dict[str, str] = {}
    total = 0
    try:
        with zipfile.ZipFile(path) as archive:
            entries = [item for item in archive.infolist() if not item.is_dir()]
            if len(entries) > MAX_FILES:
                raise ValueError(f"A skill is limited to {MAX_FILES} files")
            for item in entries:
                relative = safe_name(item.filename)
                if stat.S_ISLNK(item.external_attr >> 16):
                    raise ValueError("The ZIP contains a symlink")
                if item.file_size > MAX_FILE_BYTES:
                    raise ValueError(f"{relative} is larger than {MAX_FILE_BYTES} bytes")
                raw = archive.read(item)
                total += len(raw)
                if total > MAX_TOTAL_BYTES:
                    raise ValueError("The skill is too large")
                try:
                    collected[relative] = raw.decode("utf-8")
                except UnicodeError:
                    raise ValueError("Skills may only contain text files") from None
    except zipfile.BadZipFile:
        raise ValueError("That file is not a valid ZIP") from None
    return {name: text for name, text in strip_prefix(collected).items() if allowed(name)}


def strip_prefix(files: dict[str, str]) -> dict[str, str]:
    """A ZIP usually wraps the skill in one folder; drop it when every entry shares it."""
    if "SKILL.md" in files or not files:
        return files
    roots = {PurePosixPath(name).parts[0] for name in files}
    if len(roots) != 1:
        return files
    prefix = f"{next(iter(roots))}/"
    if not all(name.startswith(prefix) for name in files):
        return files
    return {name[len(prefix) :]: text for name, text in files.items()}


def validate_git_url(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme in {"https", "ssh"} and parsed.netloc:
        return value.strip()
    if parsed.scheme == "file" and parsed.path:
        return value.strip()
    raise ValueError("Use an https or ssh Git URL")


def from_git(value: str) -> dict[str, str]:
    url = validate_git_url(value)
    if shutil.which("git") is None:
        raise ValueError("Git is not available on this machine")
    with tempfile.TemporaryDirectory(prefix="codeharness-skill-") as temporary:
        target = Path(temporary) / "repo"
        try:
            completed = subprocess.run(
                ["git", "clone", "--depth", "1", "--single-branch", url, str(target)],
                capture_output=True,
                timeout=GIT_TIMEOUT,
                check=False,
                text=True,
            )
        except (OSError, subprocess.TimeoutExpired):
            raise ValueError("The Git clone failed or timed out") from None
        if completed.returncode != 0 or not target.is_dir():
            raise ValueError("The Git clone failed")
        nested = target / "SKILL.md"
        folder = target if nested.is_file() else next(
            (path.parent for path in target.rglob("SKILL.md") if path.is_file()), None
        )
        if folder is None:
            raise ValueError("That repository has no SKILL.md")
        return from_folder(folder)


def candidate(files: dict[str, str]) -> Candidate:
    """Validate the SKILL.md, refuse a blocked scan, and keep the exact bytes."""
    for relative in files:
        safe_name(relative)
        if not allowed(relative):
            raise ValueError(f"Unexpected file in the skill: {relative}")
    text = files.get("SKILL.md")
    if text is None:
        raise ValueError("A skill needs a SKILL.md at its root")
    parsed = frontmatter.split(text)
    declared = parsed.meta.get("name")
    fields, problem = frontmatter.validate(parsed, declared if isinstance(declared, str) else "")
    if problem:
        raise ValueError(problem)
    name = str(fields["name"])
    scripts = sorted(item for item in files if item.startswith("scripts/"))
    found = scan_text(*files.values())
    status = "blocked" if found & BLOCKING else "flagged" if found else "clean"
    scan = SkillScan(
        status=cast(ScanStatus, status), findings=sorted(found), scripts=scripts
    )
    if scan.status == "blocked":
        raise ValueError(
            "The security scan blocked this skill: " + ", ".join(sorted(found & BLOCKING))
        )
    return Candidate(name=name, files=files, scan=scan)


def build(kind: str, source: str) -> Candidate:
    if kind == "folder":
        return candidate(from_folder(Path(source)))
    if kind == "zip":
        return candidate(from_zip(Path(source)))
    if kind == "git":
        return candidate(from_git(source))
    raise ValueError("Unknown install source")


def from_write(
    name: str,
    description: str,
    body: str,
    command: str | None,
    category: str,
    requires_approval: bool,
) -> dict[str, str]:
    """One SKILL.md, rendered from the hub's form and validated like any other."""
    text = frontmatter.render(
        {
            "name": name,
            "description": description,
            "command": command,
            "category": category,
            "requires_approval": requires_approval,
            "enabled": True,
        },
        body,
    )
    return {"SKILL.md": text}


def write(folder: Path, files: dict[str, str]) -> None:
    """Write the manifest. Each file is atomic; the caller owns the failure policy."""
    from tools.atomic import atomic_write

    folder.mkdir(parents=True, exist_ok=True)
    for relative, text in sorted(files.items()):
        target = folder / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(target, text)
