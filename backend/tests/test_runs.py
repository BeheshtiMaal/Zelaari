import asyncio
import json
import socket
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from agent.bridge import RunManager
from agent.events import RunRequest
from server.app import create_app
from store.secrets import Redactor, StreamRedactor


def test_demo_order_persistence_reconnect_and_secret(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbid_network(sock: socket.socket, address: Any) -> None:
        # Windows asyncio's self-pipe uses a loopback socketpair.
        if isinstance(address, tuple) and address[0] == "127.0.0.1":
            original_connect(sock, address)
            return
        raise AssertionError("The offline demo must not use the network")

    original_connect = socket.socket.connect
    monkeypatch.setattr(socket.socket, "connect", forbid_network)
    canary = "fixture-secret-12345"
    (tmp_path / "README.md").write_text(f"# Demo\nReal file content {canary}", encoding="utf-8")
    manager = RunManager(secrets_to_redact=[canary])
    headers = {"Authorization": "Bearer fixture-token"}
    with TestClient(create_app("fixture-token", manager)) as client:
        response = client.post(
            "/runs",
            headers=headers,
            json={
                "task": "read README.md and summarize",
                "workspace": str(tmp_path),
                "model": "demo",
            },
        )
        assert response.status_code == 201, response.text
        run_id = response.json()["run_id"]
        response = client.get(f"/runs/{run_id}/events", headers=headers)
        events = [
            json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data:")
        ]
        assert events[-1]["status"] == "completed", events
        kinds = [event["type"] for event in events]
        assert kinds[0] == "run.started" and kinds[-1] == "run.finished"
        assert kinds.index("message.delta") < kinds.index("tool.call") < kinds.index("tool.result")
        assert "message.delta" in kinds[kinds.index("tool.result") + 1 :]
        assert any(
            event["type"] == "tool.result" and "Real file content" in event["text"]
            for event in events
        )
        assert [event["seq"] for event in events] == list(range(1, len(events) + 1))
        replay = client.get(f"/runs/{run_id}/events", headers={**headers, "Last-Event-ID": "3"})
        resumed = [
            json.loads(line[6:]) for line in replay.text.splitlines() if line.startswith("data:")
        ]
        assert resumed == events[3:]
        log = tmp_path / ".harness" / "runs" / run_id / "events.jsonl"
        assert [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()] == events
        assert canary not in log.read_text(encoding="utf-8")
        assert canary not in response.text
        assert canary.encode() not in (tmp_path / ".harness" / "checkpoints.sqlite").read_bytes()
        artifact = Path(__file__).resolve().parents[2] / "artifacts" / "replay-events.jsonl"
        artifact.parent.mkdir(exist_ok=True)
        artifact.write_text(log.read_text(encoding="utf-8"), encoding="utf-8")


def test_stop_is_under_one_second(tmp_path: Path) -> None:
    async def scenario() -> None:
        manager = RunManager(demo_delay=0.3)
        run_id = await manager.start(RunRequest(task="read README.md", workspace=str(tmp_path)))
        await asyncio.sleep(0.1)
        started = time.monotonic()
        await manager.stop(run_id)
        assert time.monotonic() - started < 1
        events = [event async for event in manager.events(run_id, 0)]
        assert events[-1].type == "run.finished" and events[-1].status == "stopped"
        assert sum(event.type == "run.finished" for event in events) == 1
        await manager.close()

    asyncio.run(scenario())


def test_stream_secret_split_between_chunks() -> None:
    stream = StreamRedactor(Redactor(["canary-secret"]))
    output = "".join(stream.push(part) for part in ["hello ca", "nary-", "secret world"])
    output += stream.push("", final=True)
    assert output == "hello [REDACTED] world"
