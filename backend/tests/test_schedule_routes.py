"""The schedule routes: a round trip, the refusals, and the pending count the row shows."""

import json
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from agent.events import Event, RunRequest
from permissions.types import ApprovalRecord, ApprovalRequest
from providers.base import TaskRecord
from server.app import create_app
from store.catalog import Catalog

HEADERS = {"Authorization": "Bearer token"}


class Stub:
    """Just enough of RunService: the routes never ask it to do anything else."""

    def __init__(self) -> None:
        self.started: list[RunRequest] = []
        self.pending: list[ApprovalRecord] = []

    async def recover(self) -> None:
        return None

    def approvals(self, status: str | None = None) -> list[ApprovalRecord]:
        return self.pending

    async def start(self, request: RunRequest) -> str:
        self.started.append(request)
        return "run-1"

    async def events(self, run_id: str, after: int) -> AsyncIterator[Event]:
        # The watcher follows a run to copy its outcome; this stub has no runs to follow.
        return
        yield  # pragma: no cover - makes this an async generator

    def busy(self) -> bool:
        return False

    async def close(self) -> None:
        return None


def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    (root / ".harness").mkdir(parents=True, exist_ok=True)
    return root


def body(root: Path, **overrides: object) -> dict[str, object]:
    fields: dict[str, object] = {
        "name": "Nightly tests",
        "prompt": "Run the tests and report failures",
        "workspace": str(root),
        "model": "demo",
        "time": "02:00",
    }
    fields.update(overrides)
    return fields


def client_for(tmp_path: Path, stub: Stub | None = None) -> tuple[TestClient, Catalog]:
    catalog = Catalog(tmp_path / "catalog.json")
    app = create_app("token", service=stub or Stub(), catalog=catalog)  # type: ignore[arg-type]
    return TestClient(app), catalog


def test_round_trip(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    client, _ = client_for(tmp_path)
    with client:
        created = client.post("/schedules", json=body(root), headers=HEADERS)
        assert created.status_code == 201
        record = created.json()
        assert record["id"]
        assert record["next_run_at"] is not None
        assert (record["mode"], record["ceiling"]) == ("read-only", "report")
        schedule_id = record["id"]

        listed = client.get("/schedules", headers=HEADERS)
        assert listed.status_code == 200
        payload = listed.json()
        assert [item["id"] for item in payload["schedules"]] == [schedule_id]
        assert payload["pending"] == {}
        assert payload["now"]

        updated = client.put(
            f"/schedules/{schedule_id}",
            json=body(root, name="Weekly", repeat="weekly", weekday=4, time="09:00"),
            headers=HEADERS,
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "Weekly"
        assert updated.json()["weekday"] == 4

        off = client.post(
            f"/schedules/{schedule_id}/enabled", json={"enabled": False}, headers=HEADERS
        )
        assert off.status_code == 200
        assert off.json()["enabled"] is False

        assert client.delete(f"/schedules/{schedule_id}", headers=HEADERS).status_code == 200
        assert client.get("/schedules", headers=HEADERS).json()["schedules"] == []


def test_unknown_ids_are_404(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    client, _ = client_for(tmp_path)
    with client:
        assert client.put("/schedules/nope", json=body(root), headers=HEADERS).status_code == 404
        assert client.delete("/schedules/nope", headers=HEADERS).status_code == 404
        assert (
            client.post(
                "/schedules/nope/enabled", json={"enabled": True}, headers=HEADERS
            ).status_code
            == 404
        )
        assert client.post("/schedules/nope/run", headers=HEADERS).status_code == 404
        assert client.post("/schedules/nope/skip", headers=HEADERS).status_code == 404


def test_invalid_input_is_422_without_echoing_it(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    client, _ = client_for(tmp_path)
    with client:
        for bad in (
            body(root, time="2:00"),
            body(root, repeat="weekly"),
            body(root, name="   "),
            body(root, ceiling="sometimes"),
        ):
            response = client.post("/schedules", json=bad, headers=HEADERS)
            assert response.status_code == 422
            assert response.json() == {"detail": "Invalid request"}


def test_a_workspace_that_is_not_there_is_refused(tmp_path: Path) -> None:
    client, _ = client_for(tmp_path)
    with client:
        response = client.post("/schedules", json=body(tmp_path / "gone"), headers=HEADERS)
        assert response.status_code == 400
        assert client.get("/schedules", headers=HEADERS).json()["schedules"] == []


def test_run_now_starts_one_run_with_the_effective_mode(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    stub = Stub()
    client, _ = client_for(tmp_path, stub)
    with client:
        created = client.post(
            "/schedules", json=body(root, mode="auto", ceiling="report"), headers=HEADERS
        ).json()
        response = client.post(f"/schedules/{created['id']}/run", headers=HEADERS)
        assert response.status_code == 202
        assert response.json() == {"run_id": "run-1"}
        assert len(stub.started) == 1
        assert stub.started[0].mode == "read-only"
        assert stub.started[0].schedule_id == created["id"]


def test_the_row_counts_its_own_queued_approvals(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    stub = Stub()
    client, catalog = client_for(tmp_path, stub)
    with client:
        created = client.post("/schedules", json=body(root), headers=HEADERS).json()
        catalog.data.workspaces.tasks.append(
            TaskRecord(
                id="run-1",
                workspace=str(root),
                title="Nightly tests",
                model="demo",
                schedule_id=created["id"],
            )
        )
        stub.pending = [
            ApprovalRecord(
                request=ApprovalRequest(
                    approval_id="a1", run_id="run-1", kind="tool", tool="write_file"
                ),
                interrupt_id="i1",
            ),
            # An approval from an ordinary task is not counted against any schedule.
            ApprovalRecord(
                request=ApprovalRequest(
                    approval_id="a2", run_id="run-2", kind="tool", tool="write_file"
                ),
                interrupt_id="i2",
            ),
        ]
        payload = client.get("/schedules", headers=HEADERS).json()
        assert payload["pending"] == {created["id"]: 1}


def test_schedules_require_the_token(tmp_path: Path) -> None:
    client, _ = client_for(tmp_path)
    with client:
        assert client.get("/schedules").status_code == 401
        assert client.post("/schedules", json=body(workspace(tmp_path))).status_code == 401


def test_a_created_schedule_is_on_disk_after_the_app_closes(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    client, _ = client_for(tmp_path)
    with client:
        client.post("/schedules", json=body(root), headers=HEADERS)

    stored = json.loads((tmp_path / "catalog.json").read_text(encoding="utf-8"))
    assert len(stored["schedules"]) == 1
    assert stored["schedules"][0]["next_run_at"]
    # Local wall clock, not UTC: a schedule must not move when the machine changes zone.
    assert datetime.fromisoformat(stored["schedules"][0]["created_at"]).tzinfo is None
    assert len(Catalog(tmp_path / "catalog.json").data.schedules) == 1
