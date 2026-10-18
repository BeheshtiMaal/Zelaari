"""Opt-in Phase 1 live check. Never writes credentials or provider diagnostics."""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
from providers.config import load_provider_env  # noqa: E402

load_provider_env()

from agent.bridge import RunManager  # noqa: E402 - disable inherited tracing before imports
from agent.events import RunRequest  # noqa: E402


async def main() -> None:
    with tempfile.TemporaryDirectory(prefix="codeharness-live-") as directory:
        root = Path(directory)
        (root / "README.md").write_text(
            "# Fixture\nThis project tracks migrating swallows. "
            "The verification marker is amber-orbit.\n",
            encoding="utf-8",
        )
        manager = RunManager()
        run_id = await manager.start(
            RunRequest(
                task=(
                    "Read README.md and summarize its contents in a final OpenUI Stack "
                    "with Callout and KeyValue."
                ),
                workspace=directory,
                model="openai-compatible",
            )
        )
        events = [event async for event in manager.events(run_id, 0)]
        await manager.close()
        print("Live event types:", [event.type for event in events])
        assert events[-1].type == "run.finished" and events[-1].status == "completed"
        assert any(event.type == "tool.call" and event.name == "read_file" for event in events)
        assert any(event.type == "tool.result" and "amber-orbit" in event.text for event in events)
        key = os.environ["CODEHARNESS_API_KEY"].encode()
        assert all(
            key not in file.read_bytes()
            for file in (root / ".harness").rglob("*")
            if file.is_file()
        )
        text = "".join(event.text for event in events if event.type == "message.delta")
        assert "Stack(" in text and "Callout(" in text
        print(
            "Live compatible model: completed; real read_file result; "
            "OpenUI program; no credential persisted."
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:  # noqa: BLE001 - provider errors can contain credentials
        print("Live check failed (provider diagnostics suppressed).")
        raise SystemExit(1) from None
