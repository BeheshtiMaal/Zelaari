"""Lightweight canonical workspace checks, independent of the agent runtime."""

from pathlib import Path


def workspace_root(value: str) -> Path:
    root = Path(value).resolve(strict=True)
    if not root.is_dir() or root == Path(root.anchor) or root == Path.home().resolve():
        raise ValueError("Choose a project directory, not a drive or home directory")
    return root


def storage_path(root: Path, relative: str) -> Path:
    target = (root / ".harness" / relative).resolve()
    if not target.is_relative_to(root):
        raise ValueError("Engine storage escapes workspace")
    return target
