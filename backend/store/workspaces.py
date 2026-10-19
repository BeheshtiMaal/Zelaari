"""Workspace selection and task history use canonical, jailed paths."""

import re
from pathlib import Path

from agent.events import Event, event_adapter
from providers.base import TaskRecord, Workspace, WorkspaceState
from store.catalog import Catalog
from tools.workspace import storage_path, workspace_root


def branch_name(root: Path) -> str | None:
    for folder in [root, *root.parents]:
        git = folder / ".git"
        if git.is_file():
            value = git.read_text(encoding="utf-8").strip()
            if not value.startswith("gitdir: "):
                return None
            git = (folder / value[8:]).resolve()
        if git.is_dir():
            try:
                head = (git / "HEAD").read_text(encoding="utf-8").strip()
            except OSError:
                return None
            if head.startswith("ref: refs/heads/"):
                return head[16:]
            if re.fullmatch(r"[a-fA-F0-9]{40,64}", head):
                return "detached HEAD · " + head[:8]
            return None
    return None


def select_workspace(catalog: Catalog, value: str) -> WorkspaceState:
    root = workspace_root(value)
    workspace = Workspace(path=str(root), name=root.name, branch=branch_name(root))
    state = catalog.data.workspaces
    state.recent = [
        workspace,
        *[item for item in state.recent if item.path.casefold() != str(root).casefold()],
    ][:20]
    state.selected = str(root)
    catalog.persist()
    return state


def add_task(catalog: Catalog, task: TaskRecord) -> None:
    catalog.data.workspaces.tasks.append(task)
    catalog.persist()


def workspace_state(catalog: Catalog) -> WorkspaceState:
    state = catalog.data.workspaces
    for item in state.recent:
        try:
            item.branch = branch_name(workspace_root(item.path))
        except (ValueError, OSError, RuntimeError):
            item.branch = None
            if state.selected == item.path:
                state.selected = None
                catalog.persist()
    return state


def task_events(catalog: Catalog, identifier: str) -> list[Event]:
    task = next((item for item in catalog.data.workspaces.tasks if item.id == identifier), None)
    if not task or not re.fullmatch(r"[a-f0-9]{32}", identifier):
        raise ValueError("Unknown task")
    root = workspace_root(task.workspace)
    path = storage_path(root, f"runs/{identifier}/events.jsonl")
    values = [
        event_adapter.validate_json(line) for line in path.read_text(encoding="utf-8").splitlines()
    ]
    if any(
        event.run_id != identifier or event.seq != index
        for index, event in enumerate(values, start=1)
    ):
        raise ValueError("Invalid task history")
    return values
