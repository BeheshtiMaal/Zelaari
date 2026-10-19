import asyncio
from pathlib import Path

import pytest

from agent.bridge import RunManager
from agent.events import RunRequest
from store.catalog import Catalog
from store.workspaces import branch_name, select_workspace, task_events
from tools.jail import workspace_root


def test_selection_safety_recents_and_git_metadata(tmp_path: Path) -> None:
    catalog = Catalog(tmp_path / "app" / "catalog.json")
    project = tmp_path / "project"
    project.mkdir()
    for forbidden in [str(Path.home()), str(Path(tmp_path.anchor)), str(project / "missing")]:
        with pytest.raises((ValueError, OSError)):
            select_workspace(catalog, forbidden)
    assert branch_name(project) is None
    git = project / ".git"
    git.mkdir()
    (git / "HEAD").write_text("ref: refs/heads/main\n")
    assert branch_name(project) == "main"
    (git / "HEAD").write_text("a" * 40)
    assert branch_name(project) == "detached HEAD · aaaaaaaa"
    linked = tmp_path / "linked"
    linked.mkdir()
    (linked / ".git").write_text("gitdir: ../project/.git")
    assert branch_name(linked) == "detached HEAD · aaaaaaaa"
    select_workspace(catalog, str(project))
    select_workspace(catalog, str(project / "."))
    assert len(catalog.data.workspaces.recent) == 1
    restored = Catalog(catalog.path)
    assert restored.data.workspaces.selected == str(project.resolve())
    home_alias = tmp_path / "home-alias"
    # Native Windows junction, not a mocked resolve result.
    import subprocess

    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(home_alias), str(Path.home())],
        capture_output=True,
        check=True,
    )
    with pytest.raises(ValueError):
        workspace_root(str(home_alias))


def test_completed_task_restores_and_replays_without_execution(tmp_path: Path) -> None:
    async def scenario() -> None:
        project = tmp_path / "project"
        project.mkdir()
        (project / "README.md").write_text("history-fixture")
        path = tmp_path / "app" / "catalog.json"
        catalog = Catalog(path)
        manager = RunManager(catalog=catalog)
        run_id = await manager.start(RunRequest(task="read README.md", workspace=str(project)))
        await manager.runs[run_id].task
        await manager.close()
        restored = Catalog(path)
        assert restored.data.workspaces.tasks[0].status == "completed"
        events = task_events(restored, run_id)
        assert any(
            event.type == "tool.result" and "history-fixture" in event.text for event in events
        )
        assert len(restored.data.workspaces.tasks) == 1
        with pytest.raises(ValueError):
            task_events(restored, "../escape")

    asyncio.run(scenario())
