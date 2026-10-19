import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

import agent.bridge as bridge
from agent.events import RunRequest
from providers.base import ModelInput, Probe, ProviderRecord
from providers.demo import DemoModel
from store.catalog import Catalog, Credential


def test_all_new_routes_require_auth_and_put_cors_is_locked() -> None:
    from server.app import create_app

    with TestClient(create_app("boundary-token")) as client:
        routes = [
            ("GET", "/models"),
            ("POST", "/models"),
            ("POST", "/internal/credentials"),
            ("POST", "/internal/probe"),
            ("POST", "/models/missing/test"),
            ("GET", "/presets"),
            ("GET", "/settings"),
            ("PUT", "/settings"),
            ("GET", "/workspaces"),
            ("POST", "/workspaces"),
            ("GET", "/tasks/missing/events"),
        ]
        for method, path in routes:
            assert client.request(method, path, json={}).status_code == 401
            assert (
                client.request(
                    method, path, headers={"Authorization": "Bearer wrong"}, json={}
                ).status_code
                == 401
            )
        assert (
            client.options(
                "/settings",
                headers={"Origin": "app://codeharness", "Access-Control-Request-Method": "PUT"},
            ).status_code
            == 200
        )
        assert (
            client.options(
                "/settings",
                headers={"Origin": "https://evil.invalid", "Access-Control-Request-Method": "PUT"},
            ).status_code
            == 400
        )


def test_active_run_keeps_model_and_key_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def scenario() -> None:
        catalog = Catalog()
        catalog.credential(Credential(id="mine", key=SecretStr("original-key")))
        value = ModelInput(id="mine", name="Mine", model="original", base_url="https://x/v1")
        record = catalog.save(value)
        record.probe = Probe(status="ok")
        record.supports_tools = True
        captured: list[tuple[ProviderRecord, SecretStr]] = []

        def factory(record: ProviderRecord, key: SecretStr) -> DemoModel:
            captured.append((record, key))
            return DemoModel(delay=0.01)

        monkeypatch.setattr(bridge, "chat_model", factory)
        (tmp_path / "README.md").write_text("snapshot-read-marker")
        manager = bridge.RunManager(catalog=catalog)
        identifier = await manager.start(
            RunRequest(task="read README.md", workspace=str(tmp_path), model="mine")
        )
        catalog.credential(Credential(id="mine", key=SecretStr("replacement-key")))
        catalog.save(value.model_copy(update={"model": "replacement"}))
        with pytest.raises(ValueError):
            catalog.require("mine")
        await manager.runs[identifier].task
        await manager.close()
        assert captured[0][0].model == "original"
        assert captured[0][1].get_secret_value() == "original-key"
        assert any(
            event.type == "tool.result" and "snapshot-read-marker" in event.text
            for event in manager.runs[identifier].bus.history
        )

    asyncio.run(scenario())
