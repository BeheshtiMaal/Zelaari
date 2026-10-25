"""The hub's read routes, the switches, and the four approved writes."""

import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from skills.state import load_state, save_state
from skills.types import SkillsState
from tools.jail import storage_path

HEADERS = {"Authorization": "Bearer token"}


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / ".harness").mkdir()
    return tmp_path


def client() -> TestClient:
    return TestClient(create_app("token"))


def bundled_folder(tmp_path: Path, name: str = "local-skill") -> Path:
    folder = tmp_path / "incoming" / name
    folder.mkdir(parents=True)
    (folder / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Installed from a folder.\ncommand: /local\n---\n"
        "Read the file, then edit it.\n",
        encoding="utf-8",
    )
    return folder


def approve(http: TestClient, record: dict[str, object]) -> None:
    request = record["request"]
    assert isinstance(request, dict)
    response = http.post(
        f"/runs/{request['run_id']}/interrupts/{request['approval_id']}",
        headers=HEADERS,
        json={"decision": "approve"},
    )
    assert response.status_code == 200, response.text


def reject(http: TestClient, record: dict[str, object]) -> None:
    request = record["request"]
    assert isinstance(request, dict)
    response = http.post(
        f"/runs/{request['run_id']}/interrupts/{request['approval_id']}",
        headers=HEADERS,
        json={"decision": "reject", "reason": "no"},
    )
    assert response.status_code == 200, response.text


def test_the_five_bundled_skills_are_listed(workspace: Path) -> None:
    with client() as http:
        response = http.get("/skills", headers=HEADERS, params={"workspace": str(workspace)})
    assert response.status_code == 200, response.text
    body = response.json()
    names = [item["name"] for item in body["skills"]]
    assert names == [
        "feature-spec",
        "fix-failing-tests",
        "grill-me",
        "python-project",
        "web-search",
    ]
    assert [item["command"] for item in body["commands"]] == ["/fix", "/grill", "/search", "/spec"]
    assert all(item["source"] == "bundled" for item in body["skills"])


def test_detail_returns_the_body(workspace: Path) -> None:
    with client() as http:
        response = http.get(
            "/skills/grill-me", headers=HEADERS, params={"workspace": str(workspace)}
        )
    assert response.status_code == 200
    assert "Interview" in response.json()["description"]
    assert "ask_user_question" in response.json()["body"]


def test_unknown_skill_is_404(workspace: Path) -> None:
    with client() as http:
        response = http.get("/skills/nope", headers=HEADERS, params={"workspace": str(workspace)})
    assert response.status_code == 404


def test_a_switch_is_written_and_removes_the_command(workspace: Path) -> None:
    with client() as http:
        response = http.put(
            "/skills/enabled",
            headers=HEADERS,
            params={"workspace": str(workspace)},
            json={"name": "web-search", "enabled": False},
        )
        assert response.status_code == 200, response.text
        assert response.json()["enabled"] is False
        commands = http.get(
            "/skills/commands", headers=HEADERS, params={"workspace": str(workspace)}
        ).json()
        assert "/search" not in [item["command"] for item in commands]
    assert load_state(workspace).overrides == {"web-search": False}
    assert json.loads(storage_path(workspace, "skills.json").read_text())["overrides"] == {
        "web-search": False
    }


def test_the_example_project_skill_starts_off(tmp_path: Path) -> None:
    space = tmp_path / "sample"
    source = Path(__file__).resolve().parents[2] / "examples/sample-project"
    (space / ".harness").mkdir(parents=True)
    (space / ".harness" / "skills").mkdir()
    (space / ".harness" / "skills" / "read-framework-docs").mkdir()
    text = (source / ".harness/skills/read-framework-docs/SKILL.md").read_text(encoding="utf-8")
    (space / ".harness/skills/read-framework-docs/SKILL.md").write_text(text, encoding="utf-8")
    with client() as http:
        body = http.get("/skills", headers=HEADERS, params={"workspace": str(space)}).json()
    record = next(item for item in body["skills"] if item["name"] == "read-framework-docs")
    assert record["source"] == "workspace"
    assert record["enabled"] is False
    with client() as http:
        http.put(
            "/skills/enabled",
            headers=HEADERS,
            params={"workspace": str(space)},
            json={"name": "read-framework-docs", "enabled": True},
        )
        body = http.get("/skills", headers=HEADERS, params={"workspace": str(space)}).json()
    assert next(
        item for item in body["skills"] if item["name"] == "read-framework-docs"
    )["enabled"] is True


def test_install_is_a_proposal_and_approving_writes_it(
    workspace: Path, tmp_path: Path
) -> None:
    folder = bundled_folder(tmp_path)
    with client() as http:
        response = http.post(
            "/skills/install",
            headers=HEADERS,
            params={"workspace": str(workspace)},
            json={"kind": "folder", "source": str(folder)},
        )
        assert response.status_code == 202, response.text
        assert not (workspace / ".harness" / "skills" / "local-skill").exists()
        record = response.json()
        assert record["request"]["tool"] == "skill_install"
        assert record["request"]["diff"]
        approve(http, record)
        body = http.get("/skills", headers=HEADERS, params={"workspace": str(workspace)}).json()
    assert any(item["name"] == "local-skill" for item in body["skills"])
    written = workspace / ".harness" / "skills" / "local-skill" / "SKILL.md"
    assert "Installed from a folder." in written.read_text(encoding="utf-8")


def test_rejecting_an_install_writes_nothing(workspace: Path, tmp_path: Path) -> None:
    folder = bundled_folder(tmp_path, "refused-skill")
    with client() as http:
        response = http.post(
            "/skills/install",
            headers=HEADERS,
            params={"workspace": str(workspace)},
            json={"kind": "folder", "source": str(folder)},
        )
        reject(http, response.json())
    assert not (workspace / ".harness" / "skills" / "refused-skill").exists()


def test_a_zip_install_works(workspace: Path, tmp_path: Path) -> None:
    archive = tmp_path / "skill.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr(
            "pack/SKILL.md",
            "---\nname: zipped\ndescription: From a zip.\n---\nBody\n",
        )
        bundle.writestr("pack/scripts/run.sh", "echo ok\n")
    with client() as http:
        response = http.post(
            "/skills/install",
            headers=HEADERS,
            params={"workspace": str(workspace)},
            json={"kind": "zip", "source": str(archive)},
        )
        assert response.status_code == 202, response.text
        approve(http, response.json())
    assert (workspace / ".harness/skills/zipped/scripts/run.sh").is_file()


def test_a_duplicate_install_is_refused(workspace: Path, tmp_path: Path) -> None:
    folder = bundled_folder(tmp_path, "twice")
    with client() as http:
        first = http.post(
            "/skills/install",
            headers=HEADERS,
            params={"workspace": str(workspace)},
            json={"kind": "folder", "source": str(folder)},
        )
        approve(http, first.json())
        second = http.post(
            "/skills/install",
            headers=HEADERS,
            params={"workspace": str(workspace)},
            json={"kind": "folder", "source": str(folder)},
        )
    assert second.status_code == 409


def test_create_edit_and_delete(workspace: Path) -> None:
    with client() as http:
        created = http.post(
            "/skills/create",
            headers=HEADERS,
            params={"workspace": str(workspace)},
            json={
                "name": "house-rules",
                "description": "Project conventions.",
                "body": "Always run ruff.",
                "command": "/rules",
                "category": "coding",
            },
        )
        assert created.status_code == 202, created.text
        approve(http, created.json())
        assert (workspace / ".harness/skills/house-rules/SKILL.md").is_file()

        edited = http.put(
            "/skills/house-rules",
            headers=HEADERS,
            params={"workspace": str(workspace)},
            json={
                "name": "house-rules",
                "description": "Project conventions.",
                "body": "Always run ruff and mypy.",
            },
        )
        assert edited.status_code == 202, edited.text
        approve(http, edited.json())
        text = (workspace / ".harness/skills/house-rules/SKILL.md").read_text(encoding="utf-8")
        assert "mypy" in text

        deleted = http.delete(
            "/skills/house-rules", headers=HEADERS, params={"workspace": str(workspace)}
        )
        assert deleted.status_code == 202
        approve(http, deleted.json())
    assert not (workspace / ".harness/skills/house-rules").exists()


def test_a_bundled_skill_cannot_be_edited_or_deleted(workspace: Path) -> None:
    with client() as http:
        edited = http.put(
            "/skills/grill-me",
            headers=HEADERS,
            params={"workspace": str(workspace)},
            json={"name": "grill-me", "description": "x", "body": "y"},
        )
        deleted = http.delete(
            "/skills/grill-me", headers=HEADERS, params={"workspace": str(workspace)}
        )
    assert edited.status_code == 409
    assert deleted.status_code == 409


def test_the_search_setting_is_an_approval(workspace: Path) -> None:
    with client() as http:
        response = http.put(
            "/skills/search",
            headers=HEADERS,
            params={"workspace": str(workspace)},
            json={"provider": "searxng", "endpoint": "https://search.example.test"},
        )
        assert response.status_code == 202, response.text
        assert response.json()["request"]["tool"] == "search_settings_update"
        approve(http, response.json())
        saved = http.get(
            "/skills/search", headers=HEADERS, params={"workspace": str(workspace)}
        ).json()
    assert saved == {"provider": "searxng", "endpoint": "https://search.example.test"}


def test_a_damaged_state_file_is_ignored(workspace: Path) -> None:
    storage_path(workspace, "skills.json").write_text("{not json", encoding="utf-8")
    with client() as http:
        body = http.get("/skills", headers=HEADERS, params={"workspace": str(workspace)}).json()
    assert body["skills"]
    assert load_state(workspace) == SkillsState()


def test_state_round_trips(tmp_path: Path) -> None:
    save_state(tmp_path, SkillsState(overrides={"a": True}, catalog_url="https://x.test/c.json"))
    loaded = load_state(tmp_path)
    assert loaded.overrides == {"a": True}
    assert loaded.catalog_url == "https://x.test/c.json"
