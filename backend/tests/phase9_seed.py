"""Seed the Phase 9 walkthrough: one real `render_ui` run, and one the validator refuses.

Both runs go through the product's own path — the bridge, the agent, the real validator and the
event bus — so `events.jsonl` on disk is the same file the app writes. The walkthrough reads it
instead of trusting a screenshot.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# The seed is offline by design (R19): tracing would post the run to a third party.
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"

import agent.bridge as bridge
from agent.events import RunRequest, UiRender
from store.catalog import Catalog

README = "# Report\n\nThe run changed three files.\n"


async def one(
    manager: bridge.RunManager, workspace: Path, task: str
) -> tuple[str, list[UiRender]]:
    run_id = await manager.start(RunRequest(task=task, workspace=str(workspace)))
    await manager.runs[run_id].task
    history = manager.runs[run_id].bus.history
    return run_id, [event for event in history if isinstance(event, UiRender)]


async def main() -> None:
    profile, workspace = Path(sys.argv[1]), Path(sys.argv[2])
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "README.md").write_text(README, encoding="utf-8")
    manager = bridge.RunManager(catalog=Catalog(profile / "catalog.json"), demo_delay=0)
    try:
        good_id, good = await one(manager, workspace, "demo render")
        assert len(good) == 1, f"expected one render, got {len(good)}"
        rendered = good[0]
        assert rendered.ok is True, rendered
        drawn = set(rendered.components)
        assert {"Callout", "Table", "Tabs", "KeyValue"} <= drawn, rendered.components

        bad_id, bad = await one(manager, workspace, "demo render bad")
        assert len(bad) == 1, f"expected one attempt, got {len(bad)}"
        refused = bad[0]
        assert refused.ok is False, refused
        assert refused.error and "unknown component" in refused.error, refused.error

        # The run that could not draw still finished: a refusal is a note, not a failure.
        history = manager.runs[bad_id].bus.history
        assert any(event.type == "run.finished" for event in history), (
            "the refused render stopped the run"
        )

        events = workspace / ".harness" / "runs" / good_id / "events.jsonl"
        assert events.exists(), f"the event file was not written: {events}"
        lines = [
            json.loads(line)
            for line in events.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        written = any(
            line.get("type") == "ui.render" and line.get("ok") is True for line in lines
        )
        assert written, "ui.render is not on disk"
        summary = {
            "run_id": good_id,
            "components": rendered.components,
            "refused_run_id": bad_id,
            "refused_note": refused.error,
            "events": str(events),
            "bytes": events.stat().st_size,
        }
        print(json.dumps(summary))
    finally:
        await manager.close()


if __name__ == "__main__":
    asyncio.run(main())
