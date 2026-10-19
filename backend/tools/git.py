"""Git actions the chip and the composer need, with argv-only invocation.

Branch names are validated against `git check-ref-format` rules before they reach
`argv`, so a name can never become a flag. `git switch` refuses a dirty tree itself;
this module only reports what git said and never edits `.git/HEAD`.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from tools.jail import storage_path
from tools.types import BranchSwitchResult

TIMEOUT = 30.0

_FORBIDDEN = re.compile(r"[\s~^:?*\[\\\x00-\x1f]")
"""Characters `git check-ref-format` rejects: space, control, ~ ^ : ? * [ and backslash."""


def git_executable() -> str | None:
    return shutil.which("git")


def repository(root: Path) -> Path | None:
    """The folder holding `.git`, following a worktree's `gitdir:` pointer."""
    for folder in [root, *root.parents]:
        marker = folder / ".git"
        if marker.is_dir() or marker.is_file():
            return folder
    return None


def validate_branch(value: str) -> str:
    """Reject anything that is not a plain branch name, flags included."""
    if not value or len(value) > 255:
        raise ValueError("Branch name is empty or too long")
    if value.startswith("-"):
        raise ValueError("Branch names cannot start with '-'")
    if value in {"@", "HEAD"} or ".." in value or "@{" in value:
        raise ValueError("Branch name uses a reserved form")
    if _FORBIDDEN.search(value):
        raise ValueError("Branch name contains characters git does not allow")
    if value.startswith("/") or value.endswith(("/", ".", ".lock")) or "//" in value:
        raise ValueError("Branch name has an invalid path shape")
    return value


def switch(root: Path, branch: str) -> BranchSwitchResult:
    """Run `git switch <branch>` in `root`. A failure leaves the branch unchanged."""
    name = validate_branch(branch)
    git = git_executable()
    if git is None:
        return BranchSwitchResult(error="git is not installed or not on PATH")
    try:
        done = subprocess.run(  # noqa: S603 - fixed executable, validated single argument
            [git, "switch", name],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return BranchSwitchResult(error=str(error))
    if done.returncode != 0:
        return BranchSwitchResult(error=(done.stderr or done.stdout).strip()[:2000])
    return BranchSwitchResult(branch=name)


def worktree_path(root: Path, task_id: str) -> Path:
    if not re.fullmatch(r"[a-f0-9]{32}", task_id):
        raise ValueError("Task id must be a 32-character hex id")
    return storage_path(root, f"worktrees/{task_id}")


def add_worktree(root: Path, task_id: str) -> Path:
    """Create `.harness/worktrees/<task-id>` on its own branch, ready for a manual merge."""
    target = worktree_path(root, task_id)
    if repository(root) is None:
        raise ValueError("This workspace is not a git repository")
    git = git_executable()
    if git is None:
        raise ValueError("git is not installed or not on PATH")
    target.parent.mkdir(parents=True, exist_ok=True)
    done = subprocess.run(  # noqa: S603 - fixed executable and a validated id
        [git, "worktree", "add", "-b", f"harness/{task_id}", str(target), "HEAD"],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
        check=False,
    )
    if done.returncode != 0:
        raise ValueError((done.stderr or done.stdout).strip()[:2000] or "git worktree add failed")
    return target


class SwitchInput(BaseModel):
    branch: str = Field(description="The branch to switch to, exactly as `git branch` prints it")


def build_git_switch(root: Path) -> StructuredTool:
    def run(branch: str) -> str:
        return json.dumps(switch(root, branch).model_dump(), ensure_ascii=False)

    return StructuredTool.from_function(
        func=run,
        name="git_switch",
        description=(
            "Switch the workspace to another git branch. Fails without changing anything "
            "when the tree is dirty or the branch does not exist."
        ),
        args_schema=SwitchInput,
    )
