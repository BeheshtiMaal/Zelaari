"""The About card states the real version, not a guess."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from server.app import create_app
from version import VERSION

HEADERS = {"Authorization": "Bearer token"}
ROOT = Path(__file__).resolve().parents[2]


def test_the_engine_version_matches_package_json() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    assert VERSION == package["version"]


def test_about_reports_the_version_and_the_two_locations(tmp_path: Path) -> None:
    app_data = tmp_path / "app"
    with TestClient(create_app("token", app_data=app_data)) as client:
        response = client.get("/about", headers=HEADERS)
        assert response.status_code == 200
        body = response.json()
    assert body["version"] == VERSION
    assert body["name"] == "CodeHarness"
    assert body["licence"] == "MIT"
    assert body["app_data"] == str(app_data)
    assert body["log_directory"] == str(app_data / "logs")


def test_about_is_authenticated_and_survives_a_missing_app_data(tmp_path: Path) -> None:
    with TestClient(create_app("token")) as client:
        assert client.get("/about").status_code == 401
        body = client.get("/about", headers=HEADERS).json()
    assert body["version"] == VERSION
    assert body["app_data"] == ""
    assert body["log_directory"] == ""
