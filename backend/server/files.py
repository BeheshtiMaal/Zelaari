"""`GET /files`: the workspace tree and one file, read-only.

Opening a workspace never runs a tool (R29), so this module only reads. The `.harness`
folder is hidden unless the person turns on the system-files toggle, and even then it
is served through the same jail that guards the agent.
"""

from collections.abc import Callable
from pathlib import Path

from fastapi import APIRouter, HTTPException

from tools.jail import MAX_READ_LINES, MAX_TEXT_BYTES, JailError, resolve, workspace_root
from tools.snapshot import SnapshotStore
from tools.types import FileContent, FileEntry, FileListing

PendingPaths = Callable[[], set[str]]


def _kind(path: Path) -> str:
    return "dir" if path.is_dir() else "file"


def _entries(root: Path, folder: Path, store: SnapshotStore, *, system: bool) -> list[FileEntry]:
    resolved_root = root
    items: list[FileEntry] = []
    for child in folder.iterdir():
        relative = child.relative_to(resolved_root).as_posix()
        if not system and relative.split("/")[0].casefold() == ".harness":
            continue
        try:
            size = child.stat().st_size if child.is_file() else 0
        except OSError:
            continue
        items.append(
            FileEntry(
                name=child.name,
                path=relative,
                kind=_kind(child),  # type: ignore[arg-type]
                size=size,
                changed=store.newest_for(relative) is not None,
            )
        )
    items.sort(key=lambda item: (item.kind != "dir", item.name.casefold()))
    return items


def _read(resolved: Path) -> tuple[str, bool, bool]:
    raw = resolved.read_bytes()[:MAX_TEXT_BYTES]
    if b"\x00" in raw:
        return "", True, False
    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()
    truncated = len(raw) >= MAX_TEXT_BYTES or len(lines) > MAX_READ_LINES
    return "\n".join(lines[:MAX_READ_LINES]), False, truncated


def file_routes(pending: PendingPaths | None = None) -> APIRouter:
    router = APIRouter()

    @router.get("/files")
    def files(workspace: str, path: str = "", system: bool = False) -> FileListing:
        try:
            root = workspace_root(workspace)
            target = resolve(root, path or ".", allow_protected=system)
        except (JailError, OSError):
            raise HTTPException(400, "That path is not inside the workspace") from None
        if target.is_protected and not system:
            raise HTTPException(400, "That path is not inside the workspace")

        store = SnapshotStore(root)
        if target.path.is_dir():
            try:
                entries = _entries(root, target.path, store, system=system)
            except OSError:
                raise HTTPException(400, "That folder cannot be read") from None
            return FileListing(path=target.relative, kind="dir", entries=entries)

        try:
            text, binary, truncated = _read(target.path)
        except OSError:
            raise HTTPException(400, "That file cannot be read") from None
        return FileListing(
            path=target.relative,
            kind="file",
            file=FileContent(
                path=target.relative,
                text=text,
                binary=binary,
                truncated=truncated,
                changed_lines=[] if binary else store.changed_lines(target.relative, text),
                pending_approval=target.relative in (pending() if pending else set()),
            ),
        )

    return router
