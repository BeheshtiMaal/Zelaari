"""`.harness/memory.md`: the notes a person wants every run to start with.

One file, bounded, and written only through the protected-configuration approval. It is
read at run start and injected as a block; the agent never writes it itself.
"""

from pathlib import Path

from skills.prompt import memory_block
from skills.types import MemoryDocument
from tools.jail import storage_path

LIMIT = 32_768


def path_for(root: Path) -> Path:
    return storage_path(root, "memory.md")


def load(root: Path) -> MemoryDocument:
    path = path_for(root)
    try:
        if not path.is_file() or path.is_symlink():
            return MemoryDocument(workspace=str(root), limit=LIMIT)
        if path.stat().st_size > LIMIT:
            return MemoryDocument(
                workspace=str(root),
                content="",
                bytes=path.stat().st_size,
                limit=LIMIT,
            )
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return MemoryDocument(workspace=str(root), limit=LIMIT)
    return MemoryDocument(
        workspace=str(root),
        content=text,
        bytes=len(text.encode("utf-8")),
        limit=LIMIT,
    )


def block(root: Path) -> str:
    """The prompt block, or an empty string when there is nothing to say."""
    document = load(root)
    return memory_block(document.content) if document.content.strip() else ""
