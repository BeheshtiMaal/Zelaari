"""Git: branch-name validation, a real switch, and worktree creation."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent.bridge import RunManager
from server.app import create_app
from store.catalog import Catalog
from store.secrets import Redactor
from store.workspaces import branch_name
from tools.git import add_worktree, repository, switch, validate_branch, worktree_path

GIT = shutil.which("git")
needs_git = pytest.mark.skipif(GIT is None, reason="git is not installed on this machine")


def git(root: Path, *args: str) -> str:
    done = subprocess.run(  # noqa: S603 - test helper with a fixed executable
        [GIT or "git", *args],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return done.stdout


def init_repo(root: Path) -> Path:
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "harness@example.test")
    git(root, "config", "user.name", "Harness Test")
    (root / "README.md").write_text("# Demo\n", encoding="utf-8")
    git(root, "add", "README.md")
    git(root, "commit", "-m", "initial")
    return root


# -- validation ------------------------------------------------------------
@pytest.mark.parametrize(
    "name",
    ["main", "feature/login", "release-1.2", "fix_typo", "a", "x" * 200],
)
def test_valid_branch_names_are_accepted(name: str) -> None:
    assert validate_branch(name) == name


@pytest.mark.parametrize(
    "name",
    [
        "",
        "-",
        "--force",
        "-D",
        "--",
        "a..b",
        "..",
        "a b",
        "a\tb",
        "a~1",
        "a^",
        "a:b",
        "a?",
        "a*",
        "a[b",
        "a\\b",
        "a/",
        "/a",
        "a//b",
        "a.",
        "a.lock",
        "@",
        "HEAD",
        "a@{1}",
        "x" * 256,
    ],
)
def test_unsafe_branch_names_are_rejected(name: str) -> None:
    with pytest.raises(ValueError):
        validate_branch(name)


def test_task_id_cannot_escape_the_worktree_folder(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        worktree_path(tmp_path, "../../etc")
    with pytest.raises(ValueError):
        worktree_path(tmp_path, "not-hex")
    assert worktree_path(tmp_path, "a" * 32) == tmp_path.resolve() / ".harness" / "worktrees" / (
        "a" * 32
    )


# -- real repository -------------------------------------------------------
@needs_git
def test_switch_moves_head_and_reports_the_new_branch(tmp_path: Path) -> None:
    init_repo(tmp_path)
    git(tmp_path, "branch", "feature")

    result = switch(tmp_path, "feature")

    assert result.error is None
    assert result.branch == "feature"
    assert branch_name(tmp_path) == "feature"


@needs_git
def test_flag_injection_is_refused_before_git_runs(tmp_path: Path) -> None:
    init_repo(tmp_path)

    with pytest.raises(ValueError):
        switch(tmp_path, "--force")

    assert branch_name(tmp_path) == "main"


@needs_git
def test_unknown_branch_reports_git_stderr_and_keeps_head(tmp_path: Path) -> None:
    init_repo(tmp_path)

    result = switch(tmp_path, "does-not-exist")

    assert result.branch is None
    assert result.error
    assert "does-not-exist" in result.error
    assert branch_name(tmp_path) == "main"


@needs_git
def test_dirty_tree_fails_without_changing_the_branch(tmp_path: Path) -> None:
    init_repo(tmp_path)
    # `git switch` only refuses when the local edit would be overwritten, so the
    # target branch has to disagree about the file the test edits.
    git(tmp_path, "switch", "-c", "feature")
    (tmp_path / "README.md").write_text("# Demo\nfeature version\n", encoding="utf-8")
    git(tmp_path, "commit", "-am", "feature edit")
    git(tmp_path, "switch", "main")
    (tmp_path / "README.md").write_text("# Demo\nlocal edit\n", encoding="utf-8")

    result = switch(tmp_path, "feature")

    assert result.branch is None
    assert result.error
    assert "local changes" in result.error.lower()
    assert branch_name(tmp_path) == "main"


@needs_git
def test_worktree_is_created_on_its_own_branch(tmp_path: Path) -> None:
    init_repo(tmp_path)
    task_id = "b" * 32

    target = add_worktree(tmp_path, task_id)

    assert target == tmp_path / ".harness" / "worktrees" / task_id
    assert (target / "README.md").read_text(encoding="utf-8") == "# Demo\n"
    assert branch_name(target) == f"harness/{task_id}"
    assert f"harness/{task_id}" in git(tmp_path, "branch", "--list")


def test_repository_is_none_outside_git(tmp_path: Path) -> None:
    assert repository(tmp_path) is None


# -- routes ----------------------------------------------------------------
@needs_git
def test_branch_route_switches_and_reports_errors(tmp_path: Path) -> None:
    init_repo(tmp_path)
    git(tmp_path, "branch", "feature")
    headers = {"Authorization": "Bearer token"}
    with TestClient(create_app("token")) as client:
        ok = client.post(
            "/workspaces/branch",
            headers=headers,
            json={"workspace": str(tmp_path), "branch": "feature"},
        )
        assert ok.status_code == 409, ok.text
        assert ok.json()["approval"]["tool"] == "git_switch"
        assert branch_name(tmp_path) == "main"
        approval = ok.json()["approval"]
        ok = client.post(
            f"/runs/{approval['run_id']}/interrupts/{approval['approval_id']}",
            headers=headers,
            json={"decision": "approve"},
        )
        assert ok.status_code == 200, ok.text
        assert branch_name(tmp_path) == "feature"

        bad = client.post(
            "/workspaces/branch",
            headers=headers,
            json={"workspace": str(tmp_path), "branch": "--force"},
        )
        assert bad.status_code == 400

        missing = client.post(
            "/workspaces/branch",
            headers=headers,
            json={"workspace": str(tmp_path), "branch": "nope", "approved": True},
        )
        assert missing.status_code == 409
        assert branch_name(tmp_path) == "feature"


@needs_git
def test_read_only_rules_deny_a_branch_switch(tmp_path: Path) -> None:
    init_repo(tmp_path)
    git(tmp_path, "branch", "feature")
    storage = tmp_path / ".harness"
    storage.mkdir()
    (storage / "rules.json").write_text(json.dumps({"mode": "read-only"}), encoding="utf-8")

    with TestClient(create_app("token")) as client:
        response = client.post(
            "/workspaces/branch",
            headers={"Authorization": "Bearer token"},
            json={"workspace": str(tmp_path), "branch": "feature"},
        )

    assert response.status_code == 403
    assert branch_name(tmp_path) == "main"


@needs_git
def test_approval_cannot_override_a_deny_or_read_only(tmp_path: Path) -> None:
    init_repo(tmp_path)
    git(tmp_path, "branch", "feature")
    headers = {"Authorization": "Bearer token"}
    with TestClient(create_app("token")) as client:
        body = {"workspace": str(tmp_path), "branch": "feature", "approved": True}
        denied = client.post(
            "/workspaces/branch", headers=headers, json={**body, "mode": "read-only"}
        )
        assert denied.status_code == 403
        assert branch_name(tmp_path) == "main"
        storage = tmp_path / ".harness"
        storage.mkdir(exist_ok=True)
        (storage / "rules.json").write_text(
            json.dumps({"tools": {"git_switch": [{"glob": "*", "action": "deny"}]}}),
            encoding="utf-8",
        )
        denied = client.post("/workspaces/branch", headers=headers, json=body)
        assert denied.status_code == 403
        assert branch_name(tmp_path) == "main"


@needs_git
def test_explicit_allow_switches_without_an_approval(tmp_path: Path) -> None:
    init_repo(tmp_path)
    git(tmp_path, "branch", "feature")
    storage = tmp_path / ".harness"
    storage.mkdir()
    (storage / "rules.json").write_text(
        json.dumps({"tools": {"git_switch": [{"glob": "*", "action": "allow"}]}}),
        encoding="utf-8",
    )
    with TestClient(create_app("token")) as client:
        response = client.post(
            "/workspaces/branch",
            headers={"Authorization": "Bearer token"},
            json={"workspace": str(tmp_path), "branch": "feature"},
        )
        assert response.status_code == 200
        assert branch_name(tmp_path) == "feature"


# -- worktree approval -----------------------------------------------------
@needs_git
def test_a_worktree_run_needs_approval_then_runs_in_the_worktree(tmp_path: Path) -> None:
    init_repo(tmp_path)
    catalog = Catalog(tmp_path / "catalog.json", Redactor(["token"]))
    manager = RunManager(catalog=catalog)
    headers = {"Authorization": "Bearer token"}
    body = {
        "task": "read README.md",
        "workspace": str(tmp_path),
        "model": "demo",
        "worktree": True,
    }

    with TestClient(create_app("token", manager, catalog=catalog)) as client:
        refused = client.post("/runs", headers=headers, json=body)
        assert refused.status_code == 409, refused.text
        approval = refused.json()["approval"]
        assert approval["tool"] == "worktree_create"
        assert approval["kind"] == "command"
        assert list((tmp_path / ".harness" / "worktrees").glob("*")) == []

        created = client.post(
            f"/runs/{approval['run_id']}/interrupts/{approval['approval_id']}",
            headers=headers,
            json={"decision": "approve"},
        )
        assert created.status_code == 200, created.text
        run_id = catalog.data.workspaces.tasks[-1].id

        worktree = tmp_path / ".harness" / "worktrees" / run_id
        assert worktree.relative_to(tmp_path).as_posix() == approval["path"]
        assert worktree.is_dir()
        assert branch_name(worktree) == f"harness/{run_id}"

        task = next(item for item in catalog.data.workspaces.tasks if item.id == run_id)
        assert task.workspace == str(tmp_path)
        assert task.worktree == str(worktree)
        # History stays with the workspace, so the task list and replay keep working.
        assert (tmp_path / ".harness" / "runs" / run_id / "events.jsonl").is_file()


def test_a_worktree_run_outside_git_is_refused(tmp_path: Path) -> None:
    catalog = Catalog(tmp_path / "catalog.json", Redactor(["token"]))
    manager = RunManager(catalog=catalog)
    with TestClient(create_app("token", manager, catalog=catalog)) as client:
        response = client.post(
            "/runs",
            headers={"Authorization": "Bearer token"},
            json={
                "task": "read README.md",
                "workspace": str(tmp_path),
                "model": "demo",
                "worktree": True,
                "worktree_approved": True,
            },
        )

    assert response.status_code == 400
