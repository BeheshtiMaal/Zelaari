"""Kill a real graph process between concurrent read-only delegate completions."""

import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

import pytest


@pytest.mark.parametrize("kind", ["delegate", "plan"])
def test_force_killed_delegate_preserves_completed_result_and_queued_steering(
    tmp_path: Path,
    kind: str,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "README.md").write_text("Local recovery fixture", encoding="utf-8")
    worker = Path(__file__).with_name("delegate_worker.py")
    env = {**os.environ, "PYTHONPATH": str(worker.parents[1])}
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    process = subprocess.Popen(
        [sys.executable, str(worker), str(root), "start", kind],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=flags,
    )
    try:
        assert process.stdout
        output = process.stdout
        ready: queue.Queue[bytes] = queue.Queue()
        threading.Thread(target=lambda: ready.put(output.readline()), daemon=True).start()
        assert json.loads(ready.get(timeout=90))["run_id"]
        process.kill()
        process.communicate(timeout=10)
        result = subprocess.run(
            [sys.executable, str(worker), str(root), "resume", kind],
            env=env,
            capture_output=True,
            creationflags=flags,
            timeout=90,
        )
        assert result.returncode == 0, result.stderr.decode(errors="replace")
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=10)
