"""Content-bound previews. No filesystem mutation occurs while preparing a review."""

import difflib
import hashlib
import json
from pathlib import Path
from typing import Any

from permissions.types import ApprovalRequest
from tools.jail import MAX_TEXT_BYTES, resolve_virtual


def prepare_review(root: Path, request: ApprovalRequest) -> ApprovalRequest:
    before: bytes | None = None
    after = ""
    if request.path and request.tool in {"write_file", "edit_file", "delete", "rules_update"}:
        target = resolve_virtual(root, request.path,
                                 allow_protected=request.tool == "rules_update").path
        if target.is_file():
            if target.stat().st_size > MAX_TEXT_BYTES:
                raise ValueError("File is too large to review")
            before = target.read_bytes()
        text = before.decode("utf-8") if before is not None else ""
        if request.tool in {"write_file", "rules_update"}:
            after = str(request.args.get("content", ""))
        elif request.tool == "edit_file":
            old, new = request.args.get("old_string"), request.args.get("new_string")
            if not isinstance(old, str) or not old or not isinstance(new, str):
                raise ValueError("Edit requires old_string and new_string")
            count = text.count(old)
            if count == 0 or (count > 1 and not request.args.get("replace_all")):
                raise ValueError("Edit does not uniquely match the current file")
            after = text.replace(old, new, -1 if request.args.get("replace_all") else 1)
        lines = difflib.unified_diff(
            text.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=request.path,
            tofile=request.path,
        )
        request = request.model_copy(
            update={
                "diff": "".join(
                    line if line.endswith("\n") else line + "\n\\ No newline at end of file\n"
                    for line in lines
                )
            }
        )
    digest = hashlib.sha256(
        json.dumps(
            {
                "tool": request.tool,
                "args": request.args,
                "before": before.hex() if before is not None else None,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    return request.model_copy(update={"revision": digest})


def arguments_digest(args: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(args, sort_keys=True).encode()).hexdigest()
