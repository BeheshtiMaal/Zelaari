"""Jailed workspace backend: atomic mutations, protected engine storage, no recursion on delete."""

from pathlib import Path
from typing import Protocol

from deepagents.backends import FilesystemBackend
from deepagents.backends.protocol import (
    DeleteResult,
    EditResult,
    GlobResult,
    GrepResult,
    LsResult,
    ReadResult,
    WriteResult,
)

from store.secrets import Redactor
from tools.atomic import atomic_write
from tools.jail import (
    MAX_READ_LINES,
    MAX_TEXT_BYTES,
    PROTECTED,
    JailError,
    Resolved,
    jail_message,
    resolve_virtual,
)
from tools.snapshot import SnapshotError

_BINARY_PROBE = 8192
_GREP_LIMIT = 1000


class SnapshotSink(Protocol):
    """Captures the pre-mutation state. Implemented in `tools.snapshot`."""

    def capture(self, target: Resolved, *, tool: str, call_id: str | None = None) -> str: ...


def _virtual(resolved: Resolved) -> str:
    return "/" + resolved.relative


def _visible(relative: str) -> bool:
    return relative.split("/")[0].casefold() != PROTECTED


def _denial(action: str, error: Exception, root: Path, value: str) -> str:
    """A jail block names the path and says it can never be approved.

    Anything else (a missing file, a locked handle) keeps the generic wording, because
    those are ordinary failures the model should retry differently.
    """
    if isinstance(error, JailError):
        return jail_message(root, value)
    return f"{action} denied: invalid, inaccessible, or outside workspace path"


class WorkspaceBackend(FilesystemBackend):
    """Every mutating path resolves through the jail and snapshots first."""

    def __init__(
        self,
        root: Path,
        redactor: Redactor,
        snapshots: SnapshotSink | None = None,
        *,
        call_id: str | None = None,
    ) -> None:
        super().__init__(root_dir=root, virtual_mode=True)
        self.root = root
        self.redactor = redactor
        self.snapshots = snapshots
        self.call_id = call_id

    # -- reads -------------------------------------------------------------
    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> ReadResult:
        try:
            target = resolve_virtual(self.root, file_path)
            if not target.path.is_file():
                return ReadResult(error="Read denied: not a file or outside workspace")
            if target.path.stat().st_size > MAX_TEXT_BYTES:
                return ReadResult(
                    error=f"File exceeds the {MAX_TEXT_BYTES // 1_000_000} MB read limit"
                )
            raw = target.path.read_bytes()
            if b"\x00" in raw[:_BINARY_PROBE]:
                return ReadResult(error="Binary file: read_file returns text only")
            text = self.redactor.text(raw.decode("utf-8"))
            lines = text.splitlines(keepends=True)
            start = max(0, offset)
            window = max(0, min(limit, MAX_READ_LINES))
            if window == 0:
                return ReadResult(
                    file_data={"content": "", "encoding": "utf-8"}, no_lines_requested=True
                )
            chunk = "".join(lines[start : start + window])
            end = min(start + window, len(lines))
            return ReadResult(
                file_data={"content": chunk, "encoding": "utf-8"},
                total_lines=len(lines),
                start_line=start + 1,
                end_line=end,
                next_offset=end if end < len(lines) else None,
            )
        except (JailError, OSError, RuntimeError, UnicodeError) as error:
            return ReadResult(error=_denial("Read", error, self.root, file_path))

    def ls(self, path: str) -> LsResult:
        try:
            target = resolve_virtual(self.root, path or ".")
            if not target.path.is_dir():
                return LsResult(error="Not a directory or outside workspace")
            entries: list[dict[str, object]] = []
            for child in sorted(target.path.iterdir(), key=lambda item: item.name.casefold()):
                relative = f"{target.relative}/{child.name}" if target.relative else child.name
                if not _visible(relative):
                    continue
                is_dir = child.is_dir()
                entries.append(
                    {
                        "path": "/" + relative,
                        "is_dir": is_dir,
                        "size": 0 if is_dir else child.stat().st_size,
                    }
                )
            return LsResult(entries=entries)  # type: ignore[arg-type]
        except (JailError, OSError, RuntimeError) as error:
            return LsResult(error=_denial("List", error, self.root, path))

    def glob(self, pattern: str, path: str | None = None) -> GlobResult:
        try:
            base = resolve_virtual(self.root, path or ".")
            if not base.path.is_dir():
                return GlobResult(error="Search root is not a directory or outside workspace")
            matches: list[dict[str, object]] = []
            for candidate in base.path.glob(pattern):
                try:
                    resolved = resolve_virtual(self.root, str(candidate))
                except JailError:
                    continue
                if not _visible(resolved.relative):
                    continue
                is_dir = resolved.path.is_dir()
                matches.append(
                    {
                        "path": _virtual(resolved),
                        "is_dir": is_dir,
                        "size": 0 if is_dir else resolved.path.stat().st_size,
                    }
                )
            return GlobResult(matches=matches)  # type: ignore[arg-type]
        except (JailError, OSError, RuntimeError, ValueError) as error:
            return GlobResult(error=_denial("Glob", error, self.root, path or "."))

    def grep(
        self,
        pattern: str,
        path: str | None = None,
        glob: str | None = None,
        *,
        max_count: int | None = None,
        context_lines: int = 0,
    ) -> GrepResult:
        try:
            base = resolve_virtual(self.root, path or ".")
            if not base.path.is_dir():
                return GrepResult(error="Search root is not a directory or outside workspace")
            limit = max_count if max_count is not None else _GREP_LIMIT
            context = max(0, context_lines)
            matches: list[dict[str, object]] = []
            truncated = False
            for candidate in base.path.rglob(glob or "*"):
                if len(matches) >= limit:
                    truncated = True
                    break
                try:
                    resolved = resolve_virtual(self.root, str(candidate))
                except JailError:
                    continue
                if not _visible(resolved.relative) or not resolved.path.is_file():
                    continue
                if resolved.path.stat().st_size > MAX_TEXT_BYTES:
                    continue
                try:
                    text = resolved.path.read_text(encoding="utf-8")
                except (OSError, UnicodeError):
                    continue
                lines = text.splitlines()
                for index, line in enumerate(lines):
                    if pattern not in line:
                        continue
                    match: dict[str, object] = {
                        "path": _virtual(resolved),
                        "line": index + 1,
                        "text": line,
                    }
                    if context:
                        match["context_before"] = [
                            {"line": number + 1, "text": lines[number]}
                            for number in range(max(0, index - context), index)
                        ]
                        match["context_after"] = [
                            {"line": number + 1, "text": lines[number]}
                            for number in range(index + 1, min(len(lines), index + 1 + context))
                        ]
                    matches.append(match)
                    if len(matches) >= limit:
                        truncated = True
                        break
            return GrepResult(matches=matches, truncated=truncated)  # type: ignore[arg-type]
        except (JailError, OSError, RuntimeError, ValueError) as error:
            return GrepResult(error=_denial("Grep", error, self.root, path or "."))

    # -- mutations ---------------------------------------------------------
    def _capture(self, target: Resolved, tool: str) -> None:
        if self.snapshots is not None:
            self.snapshots.capture(target, tool=tool, call_id=self.call_id)

    def write(self, file_path: str, content: str) -> WriteResult:
        try:
            target = resolve_virtual(self.root, file_path)
            if target.path.is_dir():
                return WriteResult(error="Target is a directory")
            self._capture(target, "write_file")
            atomic_write(target.path, content)
            return WriteResult(path=_virtual(target))
        except SnapshotError as error:
            return WriteResult(error=f"Blocked: {error}")
        except (JailError, OSError, RuntimeError) as error:
            return WriteResult(error=_denial("Write", error, self.root, file_path))

    def edit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> EditResult:
        try:
            target = resolve_virtual(self.root, file_path)
            if not target.path.is_file():
                return EditResult(error="Edit denied: file not found or outside workspace")
            original = target.path.read_text(encoding="utf-8")
            occurrences = original.count(old_string)
            if old_string == new_string:
                return EditResult(error="old_string and new_string are identical")
            if occurrences == 0:
                return EditResult(error="old_string was not found in the file")
            if occurrences > 1 and not replace_all:
                return EditResult(
                    error=(
                        f"old_string appears {occurrences} times; add surrounding context "
                        "or set replace_all"
                    )
                )
            updated = (
                original.replace(old_string, new_string)
                if replace_all
                else original.replace(old_string, new_string, 1)
            )
            self._capture(target, "edit_file")
            atomic_write(target.path, updated)
            return EditResult(path=_virtual(target), occurrences=occurrences if replace_all else 1)
        except SnapshotError as error:
            return EditResult(error=f"Blocked: {error}")
        except (JailError, OSError, RuntimeError, UnicodeError) as error:
            return EditResult(error=_denial("Edit", error, self.root, file_path))

    def delete(self, file_path: str) -> DeleteResult:
        try:
            target = resolve_virtual(self.root, file_path)
            if target.path.is_dir():
                return DeleteResult(error="Directories are not deleted by this tool; use a command")
            if not target.path.exists():
                return DeleteResult(error="Nothing to delete at that path")
            self._capture(target, "delete")
            target.path.unlink()
            return DeleteResult(path=_virtual(target))
        except SnapshotError as error:
            return DeleteResult(error=f"Blocked: {error}")
        except (JailError, OSError, RuntimeError) as error:
            return DeleteResult(error=_denial("Delete", error, self.root, file_path))
