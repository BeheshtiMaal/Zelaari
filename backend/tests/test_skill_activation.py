"""A leading slash command: the body joins the conversation once, and the run says so.

The prompt carries the name and the description; the body arrives as part of the person's
own instruction. That is the one place the two paths differ, so it is tested at the bridge
rather than at the block builder.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

from agent.bridge import RunManager
from agent.events import RunRequest
from store.catalog import Catalog
from store.secrets import Redactor
from tools.jail import storage_path

BODY = "BODY-TEXT-9c1d"

SKILL = f"""---
name: house-rules
description: Project conventions every change follows.
command: /house
category: coding
---

# House rules

{BODY}

Read the README before you change anything.
"""


def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    folder = root / ".harness" / "skills" / "house-rules"
    folder.mkdir(parents=True)
    (folder / "SKILL.md").write_text(SKILL, encoding="utf-8")
    (root / "README.md").write_text("# Fixture\n", encoding="utf-8")
    return root


async def until(manager: RunManager, run_id: str, done: Any) -> None:
    async with asyncio.timeout(180):
        while not done():
            await asyncio.sleep(0.02)


async def run(root: Path, tmp_path: Path, task: str) -> tuple[str, list[Any]]:
    manager = RunManager(catalog=Catalog(tmp_path / "catalog.json", Redactor()), demo_delay=0)
    run_id = await manager.start(RunRequest(task=task, workspace=str(root), mode="auto"))
    await until(manager, run_id, lambda: manager.runs[run_id].bus.finished)
    await manager.close()
    return run_id, list(manager.runs[run_id].bus.history)


def prompt_of(root: Path, run_id: str) -> str:
    return storage_path(root, f"runs/{run_id}/system.md").read_text(encoding="utf-8")


def request_of(root: Path, run_id: str) -> dict[str, Any]:
    document: dict[str, Any] = json.loads(
        storage_path(root, f"runs/{run_id}/request.json").read_text(encoding="utf-8")
    )
    return document


def test_a_slash_command_puts_the_body_in_the_instruction_once(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    run_id, events = asyncio.run(run(root, tmp_path, "/house tidy the README"))

    loaded = [event for event in events if event.type == "skill.loaded"]
    assert len(loaded) == 1, "one activation, one notice"
    assert loaded[0].name == "house-rules"
    assert loaded[0].command == "/house"
    assert loaded[0].source == "workspace"
    assert loaded[0].tokens > 0

    # The person's words survive the envelope, and the body travels with them.
    first = request_of(root, run_id)["task"]
    assert first == "/house tidy the README", "the request stays what the person typed"
    activation = storage_path(root, f"runs/{run_id}/activation.md").read_text(encoding="utf-8")
    assert "tidy the README" in activation
    assert BODY in activation
    assert activation.count(BODY) == 1, "the body is not repeated"

    # The prompt itself keeps only the name and the description.
    prompt = prompt_of(root, run_id)
    assert "house-rules: Project conventions every change follows." in prompt
    assert BODY not in prompt
    assert not any(event.type == "tool.call" and event.name == "load_skill" for event in events)


def test_a_plain_task_activates_nothing(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    run_id, events = asyncio.run(run(root, tmp_path, "tidy the README"))

    assert not any(event.type == "skill.loaded" for event in events)
    assert not storage_path(root, f"runs/{run_id}/activation.md").exists()
    assert "house-rules" in prompt_of(root, run_id)


def test_an_unknown_command_is_just_a_task(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    run_id, events = asyncio.run(run(root, tmp_path, "/nope tidy the README"))

    assert not any(event.type == "skill.loaded" for event in events)
    assert request_of(root, run_id)["task"].startswith("/nope")


def test_grill_keeps_its_interview_state_machine(tmp_path: Path) -> None:
    """`/grill` is a skill and an interview at once: the state machine still opens."""

    async def scenario() -> None:
        manager = RunManager(catalog=Catalog(tmp_path / "catalog.json", Redactor()), demo_delay=0)
        run_id = await manager.start(
            RunRequest(task="/grill improve the parser", workspace=str(tmp_path))
        )
        await until(manager, run_id, lambda: manager.questions(run_id))
        history = list(manager.runs[run_id].bus.history)
        await manager.close()
        loaded = [event for event in history if event.type == "skill.loaded"]
        assert [event.name for event in loaded] == ["grill-me"]
        assert any(event.type == "question.asked" for event in history)

    asyncio.run(scenario())
