"""Opt-in live adapter check. Never writes credentials or provider diagnostics."""

# ruff: noqa: E402
# These imports have to follow the sys.path and tracing-environment setup below, and
# `load_provider_env()` has to run before the modules that read it are imported.

import argparse
import asyncio
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
from providers.config import load_provider_env

load_provider_env()

from pydantic import SecretStr

from agent.bridge import RunManager
from agent.events import RunRequest
from providers.base import ModelInput
from providers.probe import test_connection
from store.catalog import Catalog, Credential


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=os.environ["CODEHARNESS_MODEL"])
    parser.add_argument(
        "--native-adapter",
        action="store_true",
        help="Diagnostic only: test Anthropic Messages on the configured host",
    )
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="codeharness-live-") as directory:
        root = Path(directory)
        (root / "README.md").write_text(
            "# Fixture\nThis project tracks migrating swallows. "
            "The verification marker is amber-orbit.\n",
            encoding="utf-8",
        )
        catalog = Catalog()
        catalog.credential(
            Credential(id="live", key=SecretStr(os.environ["CODEHARNESS_API_KEY"]))
        )
        catalog.save(
            ModelInput(
                id="live",
                name="Live verification",
                base_url=(
                    os.environ["CODEHARNESS_BASE_URL"].removesuffix("/v1")
                    if args.native_adapter
                    else os.environ["CODEHARNESS_BASE_URL"]
                ),
                model=args.model,
            )
        )
        if args.native_adapter:
            # Explicit diagnostic override; the product's exact-host inference stays intact.
            catalog.data.models["live"].kind = "anthropic"
        tested = await test_connection(catalog, "live")
        assert tested.supports_tools, "Connection probe failed"
        print("Model:", tested.model, "adapter:", tested.kind)
        print("Context:", tested.context.model_dump())
        manager = RunManager(catalog=catalog)
        run_id = await manager.start(
            RunRequest(
                task=(
                    "Read README.md and summarize its contents in a final OpenUI Stack "
                    "with Callout and KeyValue."
                ),
                workspace=directory,
                model="live",
            )
        )
        events = [event async for event in manager.events(run_id, 0)]
        replay = [event async for event in manager.events(run_id, 0)]
        assert replay == events
        usage = [event for event in events if event.type == "usage.updated"]
        assert usage
        print(
            "Usage:",
            usage[-1].input_tokens,
            usage[-1].output_tokens,
            "estimated:",
            usage[-1].estimated,
        )
        print("Reasoning received:", any(e.type == "reasoning.delta" for e in events))
        stopped_id = await manager.start(
            RunRequest(
                task="Read README.md and explain the contents in detail.",
                workspace=directory,
                model="live",
            )
        )
        await manager.stop(stopped_id)
        stopped = [event async for event in manager.events(stopped_id, 0)]
        assert stopped[-1].type == "run.finished" and stopped[-1].status == "stopped"
        await manager.close()
        assert events[-1].type == "run.finished" and events[-1].status == "completed"
        assert any(
            event.type == "tool.call" and event.name == "read_file" for event in events
        )
        assert any(
            event.type == "tool.result" and "amber-orbit" in event.text
            for event in events
        )
        key = os.environ["CODEHARNESS_API_KEY"].encode()
        assert all(
            key not in file.read_bytes()
            for file in (root / ".harness").rglob("*")
            if file.is_file()
        )
        text = "".join(event.text for event in events if event.type == "message.delta")
        assert "Stack(" in text and "Callout(" in text
        print(
            "Live adapter: completed; real read_file result; OpenUI program; "
            "replay identical; Stop passed; no credential persisted."
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:  # noqa: BLE001 - provider errors can contain credentials
        print("Live check failed (provider diagnostics suppressed).")
        raise SystemExit(1) from None
