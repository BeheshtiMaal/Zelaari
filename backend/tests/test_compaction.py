"""Compaction follows the settings, and its summary is what a new chat starts from."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import HumanMessage

from agent.bridge import RunManager
from agent.events import RunRequest
from agent.factory import summarizer
from agent.summarization import (
    SUMMARY_LIMIT,
    read_summary,
    save_summary,
    seed_block,
    summary_path,
)
from providers.base import TaskRecord
from server.app import create_app
from store.catalog import Catalog
from store.secrets import Redactor
from store.workspaces import add_task
from tools.jail import storage_path
from verify.settings import ContextSettings

RUN = "a" * 12


def settings(**values: Any) -> ContextSettings:
    return ContextSettings.model_validate(
        {"compaction_percent": 60, "keep_messages": 8, "offload": True, "show_ring": True}
        | values
    )


def change(text: str) -> dict[str, Any]:
    return {"_summarization_event": {"summary_message": HumanMessage(content=text)}}


def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir(exist_ok=True)
    (root / "README.md").write_text("# Fixture\n", encoding="utf-8")
    return root


def applied(built: Any) -> tuple[Any, Any]:
    """The trigger and keep the installed summarizer actually runs with."""
    helper = built._lc_helper
    return helper.trigger, helper.keep


def test_the_summarizer_is_built_from_the_context_settings(tmp_path: Path) -> None:
    from providers.demo import DemoModel

    # The demo model publishes no window, so the percentage becomes real tokens.
    built = summarizer(
        DemoModel(),
        workspace(tmp_path),
        Redactor(),
        None,
        settings(compaction_percent=75),
        128_000,
    )
    assert applied(built) == (("tokens", 96_000), ("messages", 8))
    tight = summarizer(
        DemoModel(),
        workspace(tmp_path),
        Redactor(),
        None,
        settings(compaction_percent=30, keep_messages=2),
        2_000,
    )
    assert applied(tight) == (("tokens", 600), ("messages", 2))
    # No window at all: the installed defaults stay in charge instead of guessing.
    blind = summarizer(DemoModel(), workspace(tmp_path), Redactor(), None, settings())
    assert applied(blind)[0] == ("tokens", 170_000)


def test_a_model_that_publishes_a_window_takes_the_fraction(tmp_path: Path) -> None:
    from providers.demo import DemoModel

    profiled = DemoModel(profile={"max_input_tokens": 200_000})
    built = summarizer(
        profiled, workspace(tmp_path), Redactor(), None, settings(compaction_percent=60)
    )
    assert applied(built)[0] == ("fraction", 0.6)


def test_the_summary_file_is_redacted_and_bounded(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    save_summary(root, RUN, change("x" * (SUMMARY_LIMIT + 500)), True)
    written = summary_path(root, RUN)
    assert written == storage_path(root, f"context/summaries/{RUN}.md")
    assert len(written.read_text(encoding="utf-8")) == SUMMARY_LIMIT
    assert read_summary(root, RUN) is not None


def test_offload_off_keeps_no_summary(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    save_summary(root, RUN, change("a summary"), False)
    assert not summary_path(root, RUN).exists()
    assert read_summary(root, RUN) is None


def test_updates_without_a_summary_are_ignored(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    save_summary(root, RUN, {"messages": []}, True)
    save_summary(root, RUN, {"_summarization_event": {"summary_message": None}}, True)
    save_summary(root, RUN, change("   "), True)
    assert not summary_path(root, RUN).exists()


def test_the_handoff_block_is_bounded() -> None:
    block = seed_block("y" * (SUMMARY_LIMIT + 100))
    assert block.startswith("Previous conversation summary")
    assert len(block) < SUMMARY_LIMIT + 40


def test_seeding_reads_the_previous_summary(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    save_summary(root, RUN, change("We changed the parser."), True)
    manager = RunManager(catalog=Catalog(tmp_path / "catalog.json", Redactor()))
    seeded = manager.seeded(root, "keep going", RUN)
    assert seeded.endswith("keep going")
    assert "We changed the parser." in seeded
    assert manager.seeded(root, "keep going", None) == "keep going"
    with pytest.raises(ValueError):
        manager.seeded(root, "keep going", "b" * 12)


def catalog_with_run(tmp_path: Path, root: Path) -> Catalog:
    catalog = Catalog(tmp_path / "catalog.json", Redactor())
    add_task(
        catalog,
        TaskRecord(
            id=RUN, workspace=str(root), title="task", model="demo", mode="auto", worktree=None
        ),
    )
    return catalog


def test_the_summary_route_serves_the_file_or_404(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    catalog = catalog_with_run(tmp_path, root)
    headers = {"Authorization": "Bearer test-token"}
    with TestClient(create_app("test-token", catalog=catalog)) as client:
        assert client.get(f"/runs/{RUN}/summary", headers=headers).status_code == 404
        save_summary(root, RUN, change("A compacted history."), True)
        response = client.get(f"/runs/{RUN}/summary", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert (body["run_id"], body["summary"]) == (RUN, "A compacted history.")
        assert datetime.fromisoformat(body["created_at"]).tzinfo is not None


def test_a_real_seeded_run_starts_with_the_summary_block(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    storage_path(root, "").mkdir(parents=True, exist_ok=True)
    storage_path(root, "config.json").write_text(
        json.dumps({"verify": {"gate": False, "command": "echo ok"}}), encoding="utf-8"
    )
    save_summary(root, RUN, change("Earlier we fixed the parser and left notes.txt alone."), True)

    async def scenario() -> tuple[dict[str, Any], list[Any]]:
        manager = RunManager(catalog=Catalog(tmp_path / "catalog.json", Redactor()))
        run_id = await manager.start(
            RunRequest(
                task="demo verify gate",
                workspace=str(root),
                mode="auto",
                seed_summary_from=RUN,
            )
        )
        async with asyncio.timeout(90):
            while not any(
                event.type == "run.finished" for event in manager.runs[run_id].bus.history
            ):
                await asyncio.sleep(0.02)
        await manager.close()
        request = json.loads(
            storage_path(root, f"runs/{run_id}/request.json").read_text(encoding="utf-8")
        )
        return request, list(manager.runs[run_id].bus.history)

    request, events = asyncio.run(scenario())
    assert request["seed_summary_from"] == RUN
    assert request["task"].startswith("Previous conversation summary")
    assert "Earlier we fixed the parser" in request["task"]
    assert request["task"].endswith("demo verify gate")
    # The timeline still shows the person's task, not the handoff block.
    started = next(event for event in events if event.type == "run.started")
    assert started.task == "demo verify gate"
    assert events[-1].type == "run.finished"
