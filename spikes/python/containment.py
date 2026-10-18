"""Disposable Windows resolve-and-contain candidate; not race resistant."""

from pathlib import Path, PureWindowsPath


def contained(root: Path, value: str) -> Path:
    windows = PureWindowsPath(value)
    if windows.drive.startswith("\\\\") or (windows.drive and not windows.root):
        raise ValueError("UNC and drive-relative paths are unsupported")
    if windows.root and not windows.drive:
        raise ValueError("Root-relative paths are ambiguous")
    root = root.resolve(strict=True)
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    target = candidate.resolve(strict=False)
    if not target.is_relative_to(root):
        raise ValueError("Path escapes workspace")
    return target
