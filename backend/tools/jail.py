"""Read-only filesystem backend. Resolve-based containment is not an OS sandbox."""

import re
from pathlib import Path, PureWindowsPath

from deepagents.backends import FilesystemBackend
from deepagents.backends.protocol import EditResult, ReadResult, WriteResult

from store.secrets import Redactor


def workspace_root(value: str) -> Path:
    root = Path(value).resolve(strict=True)
    if not root.is_dir() or root == Path(root.anchor) or root == Path.home().resolve():
        raise ValueError("Choose a project directory, not a drive or home directory")
    return root


def contained(root: Path, value: str) -> Path:
    windows = PureWindowsPath(value)
    if windows.drive.startswith("\\\\") or (windows.drive and not windows.root):
        raise ValueError("UNC, device and drive-relative paths are unsupported")
    if windows.root and not windows.drive:
        raise ValueError("Root-relative paths are unsupported; use a relative path")
    if any(part in {"..", ".harness"} for part in windows.parts):
        raise ValueError("Traversal and engine storage are protected")
    if any(":" in part for part in windows.parts[1:] if windows.drive) or (
        not windows.drive and ":" in value
    ):
        raise ValueError("Alternate data streams are unsupported")
    if re.search(r"(^|[/\\])(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)", value, re.I):
        raise ValueError("Device names are unsupported")
    path = Path(value)
    target = (path if path.is_absolute() else root / path).resolve()
    if not target.is_relative_to(root):
        raise ValueError("Path escapes workspace")
    return target


def storage_path(root: Path, relative: str) -> Path:
    target = (root / ".harness" / relative).resolve()
    if not target.is_relative_to(root):
        raise ValueError("Engine storage escapes workspace")
    return target


class ReadOnlyBackend(FilesystemBackend):
    def __init__(self, root: Path, redactor: Redactor) -> None:
        super().__init__(root_dir=root, virtual_mode=True)
        self.root = root
        self.redactor = redactor

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> ReadResult:
        try:
            target = contained(self.root, file_path)
            if target.stat().st_size > 2_000_000:
                return ReadResult(error="File exceeds Phase 1 text read limit (2 MB)")
            text = self.redactor.text(target.read_text(encoding="utf-8"))
            lines = text.splitlines(keepends=True)
            content = "".join(lines[max(0, offset) : max(0, offset) + max(0, min(limit, 2000))])
            return ReadResult(file_data={"content": content, "encoding": "utf-8"})
        except (ValueError, OSError, RuntimeError, UnicodeError):
            return ReadResult(error="Read denied: invalid, inaccessible, or outside workspace path")

    def write(self, file_path: str, content: str) -> WriteResult:
        return WriteResult(error="Phase 1 allows file reads only")

    def edit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> EditResult:
        return EditResult(error="Phase 1 allows file reads only")
