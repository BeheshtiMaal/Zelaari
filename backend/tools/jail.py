"""Workspace containment. Resolve-based checks are not an OS sandbox.

Phase 0 recorded the residual race: a junction created between resolution and the
open call can still redirect a write. We resolve every path (symlinks and NTFS
junctions included) and reject anything that lands outside the root, but we do not
claim kernel-level isolation.
"""

import re
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

PROTECTED = ".harness"
MAX_TEXT_BYTES = 2_000_000
MAX_READ_LINES = 2000

_DEVICE = re.compile(r"(^|[/\\])(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)", re.I)


class JailError(ValueError):
    """A path that must never reach the filesystem."""


@dataclass(frozen=True)
class Resolved:
    """A path proven to live inside the workspace, plus its POSIX-relative form."""

    path: Path
    relative: str

    @property
    def is_protected(self) -> bool:
        return self.relative.split("/")[0].casefold() == PROTECTED


def workspace_root(value: str) -> Path:
    root = Path(value).resolve(strict=True)
    if not root.is_dir() or root == Path(root.anchor) or root == Path.home().resolve():
        raise JailError("Choose a project directory, not a drive or home directory")
    return root


def storage_path(root: Path, relative: str) -> Path:
    target = (root / PROTECTED / relative).resolve()
    if not target.is_relative_to(root):
        raise JailError("Engine storage escapes workspace")
    return target


BLOCK_NOTE = "Access is never allowed, even with approval."


def jail_message(root: Path, value: str) -> str:
    """The one sentence a jail rejection produces, for the model and the error card.

    The renderer recognises the prefix and renders the block card, so this string is
    part of the contract: change it in both places or not at all.
    """
    try:
        target = str((root / value).resolve())
    except (OSError, ValueError):
        target = value
    return f"Access blocked: {target} is outside the workspace. {BLOCK_NOTE}"


def _reject_forms(value: str) -> None:
    """Reject the spellings that bypass a naive relative-path join."""
    windows = PureWindowsPath(value)
    if windows.drive.startswith("\\\\") or (windows.drive and not windows.root):
        raise JailError("UNC, device and drive-relative paths are unsupported")
    if windows.root and not windows.drive:
        raise JailError("Root-relative paths are unsupported; use a relative path")
    if any(part.casefold() == ".." for part in windows.parts):
        raise JailError("Traversal is not allowed")
    if any(":" in part for part in windows.parts[1:] if windows.drive) or (
        not windows.drive and ":" in value
    ):
        raise JailError("Alternate data streams are unsupported")
    if _DEVICE.search(value):
        raise JailError("Device names are unsupported")


def resolve(root: Path, value: str, *, allow_protected: bool = False) -> Resolved:
    """Resolve `value` inside `root` or raise `JailError`.

    `allow_protected` exists only for engine-owned paths (snapshots, run logs); no
    agent-facing tool may set it.
    """
    _reject_forms(value)
    candidate = Path(value)
    target = (candidate if candidate.is_absolute() else root / candidate).resolve()
    if not target.is_relative_to(root):
        raise JailError("Path escapes workspace")
    relative = target.relative_to(root).as_posix()
    if relative == ".":
        relative = ""
    if not allow_protected and relative.split("/")[0].casefold() == PROTECTED:
        raise JailError("Engine storage is protected")
    if any(part.casefold() == PROTECTED for part in target.relative_to(root).parts):
        if not allow_protected:
            raise JailError("Engine storage is protected")
    return Resolved(target, relative)


def virtual_path(value: str) -> str:
    """Map the middleware's canonical `/path` form back to a workspace-relative path."""
    return value[1:] if value.startswith("/") and not value.startswith("//") else value


def resolve_virtual(root: Path, value: str, *, allow_protected: bool = False) -> Resolved:
    return resolve(root, virtual_path(value), allow_protected=allow_protected)
