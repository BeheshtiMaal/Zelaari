"""The sample project is copied once, and never overwrites what the person changed."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from appdata import sample
from providers.base import WorkspaceState
from server.app import create_app
from store.catalog import Catalog

HEADERS = {"Authorization": "Bearer token"}


def bundle(tmp_path: Path) -> Path:
    root = tmp_path / "bundle"
    (root / ".harness" / "skills" / "read-framework-docs").mkdir(parents=True)
    (root / "README.md").write_text("# Sample project\n", encoding="utf-8")
    (root / ".harness" / "skills" / "read-framework-docs" / "SKILL.md").write_text(
        "---\nname: read-framework-docs\ndescription: Read docs.\nenabled: false\n---\n",
        encoding="utf-8",
    )
    return root


def test_the_bundled_sample_exists_in_this_checkout() -> None:
    found = sample.source()
    assert found is not None
    assert (found / "README.md").is_file()
    assert (found / ".harness" / "skills" / "read-framework-docs" / "SKILL.md").is_file()


def test_it_is_copied_into_app_data_with_its_project_skill(tmp_path: Path) -> None:
    destination = sample.materialise(bundle(tmp_path), tmp_path / "data")
    assert destination == tmp_path / "data" / "sample-project"
    assert (destination / "README.md").is_file()
    assert (destination / ".harness" / "skills" / "read-framework-docs" / "SKILL.md").is_file()


def test_a_second_copy_never_overwrites_the_persons_edits(tmp_path: Path) -> None:
    source = bundle(tmp_path)
    destination = sample.materialise(source, tmp_path / "data")
    (destination / "README.md").write_text("# My notes\n", encoding="utf-8")
    again = sample.materialise(source, tmp_path / "data")
    assert again == destination
    assert (again / "README.md").read_text(encoding="utf-8") == "# My notes\n"


def test_a_build_without_the_sample_says_so_instead_of_inventing_one() -> None:
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(sample, "source", lambda: None)
        app = create_app("token", catalog=Catalog(), app_data=None)
        response = TestClient(app).post("/workspaces/sample", headers=HEADERS)
    assert response.status_code == 404
    assert "sample" in response.json()["detail"].lower()


def test_opening_the_sample_selects_it_as_the_workspace(tmp_path: Path) -> None:
    source = bundle(tmp_path)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(sample, "source", lambda: source)
        app = create_app(
            "token", catalog=Catalog(tmp_path / "profile.json"), app_data=tmp_path / "data"
        )
        response = TestClient(app).post("/workspaces/sample", headers=HEADERS)
    assert response.status_code == 200
    state = WorkspaceState.model_validate(response.json())
    assert state.selected == str(tmp_path / "data" / "sample-project")
    assert any(item.path == state.selected for item in state.recent)


def test_the_sample_route_needs_the_token(tmp_path: Path) -> None:
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(sample, "source", lambda: bundle(tmp_path))
        app = create_app(
            "token", catalog=Catalog(tmp_path / "profile.json"), app_data=tmp_path / "data"
        )
        response = TestClient(app).post("/workspaces/sample")
    assert response.status_code == 401
