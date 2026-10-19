"""Force-kill real engine processes, rebuild graph, and inspect observable effects."""

import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil
import pytest


@pytest.mark.parametrize("scenario", ["pending", "executing", "after-result"])
def test_force_kill_engine_does_not_replay_effects(tmp_path: Path, scenario: str) -> None:
    root = tmp_path / "project"
    root.mkdir()
    worker = Path(__file__).with_name("approval_worker.py")
    environment = {**os.environ, "PYTHONPATH": str(worker.parents[1])}
    process = subprocess.Popen(
        [sys.executable, str(worker), str(root), scenario, "start"],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    try:
        if scenario == "after-result":
            assert process.wait(timeout=30) == 71
            assert (root / "launches.txt").exists()
        else:
            ready: queue.Queue[bytes] = queue.Queue()
            assert process.stdout is not None
            output = process.stdout
            threading.Thread(target=lambda: ready.put(output.readline()), daemon=True).start()
            message = ready.get(timeout=30)
            assert json.loads(message)["ready"]
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=10)
        if scenario == "executing":
            shell_pid = int((root / "shell.pid").read_text(encoding="utf-8-sig").strip())
            for _ in range(80):
                if not psutil.pid_exists(shell_pid):
                    break
                time.sleep(0.025)
            assert not psutil.pid_exists(shell_pid), "command survived engine termination"
        resumed = subprocess.run(
            [sys.executable, str(worker), str(root), scenario, "resume"],
            env=environment,
            capture_output=True,
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        assert resumed.returncode == 0, resumed.stderr.decode(errors="replace")
        if scenario == "pending":
            assert (root / "a.txt").read_text() == "a.txt"
            assert not (root / "b.txt").exists()
        else:
            assert (root / "launches.txt").read_text().splitlines() == ["launch"]
            events = next((root / ".harness/runs").glob("*/events.jsonl")).read_text()
            assert "Interrupted:" in events
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=10)
