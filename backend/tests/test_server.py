import importlib
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from store.catalog import Catalog


def test_auth_and_locked_cors() -> None:
    with TestClient(create_app("test-token")) as client:
        assert client.get("/health").status_code == 401
        assert client.get("/health", headers={"Authorization": "Bearer wrong"}).status_code == 401
        headers = {"Authorization": "Bearer test-token"}
        assert client.get("/health", headers=headers).json() == {"status": "ok"}
        response = client.get("/health", headers={**headers, "Origin": "https://evil.invalid"})
        assert "access-control-allow-origin" not in response.headers
        response = client.get("/health", headers={**headers, "Origin": "app://codeharness"})
        assert response.headers["access-control-allow-origin"] == "app://codeharness"


def test_explicit_development_mode_only() -> None:
    with pytest.raises(ValueError):
        create_app("")
    with TestClient(create_app("", dev=True)) as client:
        assert client.get("/health").status_code == 200


def test_agent_import_warmup_never_blocks_the_event_loop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Importing the agent stack costs seconds on Windows. Startup must hand it to a worker
    # thread so health, settings and stop stay responsive, and the first manager request
    # joins that thread instead of importing inline.
    real = importlib.import_module
    entered, release = threading.Event(), threading.Event()
    threads: list[str] = []

    def gated(name: str, package: str | None = None) -> object:
        if name == "agent.bridge":
            threads.append(threading.current_thread().name)
            entered.set()
            release.wait(10)
        return real(name, package)

    monkeypatch.setattr("server.app.importlib.import_module", gated)
    started = time.monotonic()
    with TestClient(create_app("test-token", catalog=Catalog(tmp_path / "catalog.json"))) as client:
        assert time.monotonic() - started < 0.5
        assert entered.wait(10), "The agent import must start at startup"
        headers = {"Authorization": "Bearer test-token"}
        health = time.monotonic()
        assert client.get("/health", headers=headers).status_code == 200
        assert time.monotonic() - health < 0.3
        release.set()
        assert client.get("/approvals", headers=headers).status_code == 200
    assert threads and threads[0] != threading.current_thread().name


def test_concurrent_first_requests_share_one_manager(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Two managers in one process would restore the same runs twice, duplicate checkpoints
    # and keep the workspace's SQLite file open past shutdown: only the last manager is
    # closed by the lifespan.
    real_import = importlib.import_module
    entered, release = threading.Event(), threading.Event()

    def gated(name: str, package: str | None = None) -> object:
        if name == "agent.bridge":
            entered.set()
            release.wait(10)
        return real_import(name, package)

    monkeypatch.setattr("server.app.importlib.import_module", gated)
    bridge = real_import("agent.bridge")
    created: list[int] = []
    real_manager = bridge.RunManager

    class Counting(real_manager):  # type: ignore[misc, valid-type]
        def __init__(self, *args: object, **kwargs: object) -> None:
            created.append(id(self))
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(bridge, "RunManager", Counting)
    headers = {"Authorization": "Bearer test-token"}
    with TestClient(create_app("test-token", catalog=Catalog(tmp_path / "catalog.json"))) as client:
        assert entered.wait(10), "The agent import must start at startup"
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [
                pool.submit(client.get, "/approvals", headers=headers) for _ in range(4)
            ]
            time.sleep(0.3)
            release.set()
            statuses = [future.result(30).status_code for future in futures]
    assert statuses == [200, 200, 200, 200]
    assert len(created) == 1

