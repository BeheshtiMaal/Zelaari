"""The app preferences: defaults from the mock, a merge that never resets, and hard bounds."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from providers.base import Appearance, Settings
from server.app import create_app
from store.catalog import Catalog

HEADERS = {"Authorization": "Bearer token"}


def test_the_defaults_are_the_ones_the_mock_shows() -> None:
    value = Settings()
    assert value.locale == "fa"
    assert value.default_mode == "ask"
    assert value.retention_days == 30
    assert value.appearance.theme == "dark"
    assert value.appearance.font == "medium"
    assert value.appearance.show_thinking is True
    assert value.appearance.keep_thinking_open is True
    assert value.appearance.show_terminal is True


def test_preferences_survive_a_restart(tmp_path: Path) -> None:
    path = tmp_path / "catalog.json"
    saved = Catalog(path).settings(
        Settings(
            locale="en",
            default_mode="auto",
            retention_days=7,
            appearance=Appearance(
                theme="light", font="large", show_thinking=False, keep_thinking_open=False
            ),
        )
    )
    restored = Catalog(path).data.settings
    assert restored == saved
    assert restored.appearance.theme == "light"
    assert restored.appearance.font == "large"
    assert restored.appearance.show_terminal is True
    assert restored.retention_days == 7


def test_a_partial_payload_does_not_reset_the_preferences_it_omits(tmp_path: Path) -> None:
    catalog = Catalog(tmp_path / "catalog.json")
    catalog.settings(Settings(appearance=Appearance(theme="light", font="large")))
    # A caller that only knows about the locale must not put the theme back to dark.
    merged = catalog.settings(Settings(locale="en"))
    assert merged.locale == "en"
    assert merged.appearance.theme == "light"
    assert merged.appearance.font == "large"
    assert merged.retention_days == 30


@pytest.mark.parametrize(
    "payload",
    [
        {"appearance": {"theme": "neon"}},
        {"appearance": {"font": "huge"}},
        {"appearance": {"show_thinking": "maybe"}},
        {"default_mode": "yolo"},
        {"retention_days": -1},
        {"retention_days": 3651},
        {"locale": "fr"},
        {"appearance": {"contrast": "high"}},
    ],
)
def test_a_bad_value_never_reaches_the_store(tmp_path: Path, payload: dict[str, object]) -> None:
    catalog = Catalog(tmp_path / "catalog.json")
    with TestClient(create_app("token", catalog=catalog)) as client:
        assert client.put("/settings", headers=HEADERS, json=payload).status_code == 422
    assert catalog.data.settings == Settings()


def test_the_route_returns_the_saved_preferences() -> None:
    catalog = Catalog()
    with TestClient(create_app("token", catalog=catalog)) as client:
        body = {"locale": "en", "default_mode": "read-only", "retention_days": 90,
                "appearance": {"theme": "system", "font": "small"}}
        response = client.put("/settings", headers=HEADERS, json=body)
        assert response.status_code == 200
        assert response.json() == {
            "locale": "en",
            "default_model": None,
            "default_mode": "read-only",
            "retention_days": 90,
            "appearance": {
                "theme": "system",
                "font": "small",
                "show_thinking": True,
                "keep_thinking_open": True,
                "show_terminal": True,
            },
        }
        assert client.get("/settings", headers=HEADERS).json() == response.json()


def test_an_untested_default_model_is_still_rejected() -> None:
    catalog = Catalog()
    with TestClient(create_app("token", catalog=catalog)) as client:
        response = client.put(
            "/settings", headers=HEADERS, json={"default_model": "not-tested", "locale": "en"}
        )
        assert response.status_code == 400
    assert catalog.data.settings.locale == "fa"


def test_the_bounds_are_enforced_by_the_contract() -> None:
    with pytest.raises(ValidationError):
        Settings(retention_days=4000)
    with pytest.raises(ValidationError):
        Settings(appearance=Appearance(theme="light", font="giant"))  # type: ignore[arg-type]
    # Zero means keep everything, so it has to stay legal.
    assert Settings(retention_days=0).retention_days == 0
