from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from providers.base import ModelInput, Settings
from server.app import create_app
from store.catalog import Catalog, Credential


def test_catalog_persistence_and_memory_only_keys(tmp_path: Path) -> None:
    path = tmp_path / "catalog.json"
    catalog = Catalog(path)
    value = ModelInput(id="mine", name="Mine", base_url="https://example.invalid/v1", model="m")
    with pytest.raises(ValueError):
        catalog.save(value)
    catalog.credential(Credential(id="mine", key=SecretStr("synthetic-canary-239")))
    assert catalog.save(value).key_suffix == "-239"
    with pytest.raises(ValueError):
        catalog.settings(Settings(default_model="mine"))
    catalog.settings(Settings(locale="en", default_model="demo"))
    restored = Catalog(path)
    assert restored.data.settings.locale == "en"
    assert not restored.keys
    assert restored.records()[1].probe.code == "vault"
    assert "synthetic-canary-239" not in path.read_text()
    value.name = "synthetic-canary-239"
    with pytest.raises(ValueError):
        catalog.save(value)


def test_model_auth_validation_and_write_only_credentials() -> None:
    catalog = Catalog()
    with TestClient(create_app("token", catalog=catalog)) as client:
        assert client.get("/models").status_code == 401
        headers = {"Authorization": "Bearer token"}
        assert (
            client.post(
                "/internal/credentials",
                headers=headers,
                json={"id": "bad/secret", "key": "canary-credential"},
            ).text
            == '{"detail":"Invalid request"}'
        )
        assert client.get("/internal/credentials", headers=headers).status_code == 405
        response = client.post(
            "/internal/credentials",
            headers=headers,
            json={"id": "mine", "key": "canary-credential"},
        )
        assert response.json() == {"status": "ok"}
        assert "canary-credential" not in client.get("/models", headers=headers).text
        assert (
            client.put(
                "/settings", headers=headers, json={"locale": "en", "default_model": "demo"}
            ).status_code
            == 200
        )
