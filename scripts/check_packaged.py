"""Exercise the PyInstaller engine/watchdog with no Python child or host secrets."""

import json
import os
import queue
import subprocess
import tempfile
import threading
from pathlib import Path

import httpx
import psutil

root = Path(__file__).resolve().parents[1]
env = {
    name: value
    for name, value in os.environ.items()
    if name.upper() in {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATH", "USERPROFILE"}
}
process = subprocess.Popen(
    [
        str(root / "build/engine/watchdog/watchdog.exe"),
        str(root / "build/engine/engine/engine.exe"),
    ],
    cwd=root,
    env=env,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    encoding="utf-8",
)
owned: list[psutil.Process] = []
try:
    assert process.stdin is not None and process.stdout is not None
    process.stdin.write(
        json.dumps({"token": "packaged-fixture-token", "provider": {}}) + "\n"
    )
    process.stdin.flush()
    lines: queue.Queue[str] = queue.Queue()
    threading.Thread(
        target=lambda: lines.put(process.stdout.readline()), daemon=True
    ).start()
    line = lines.get(timeout=30)
    if not line:
        raise RuntimeError("Packaged engine did not announce a port")
    port = json.loads(line)["port"]
    owned = psutil.Process(process.pid).children(recursive=True)
    assert any(child.name() == "engine.exe" for child in owned)
    assert not any(
        child.name().lower() in {"python.exe", "pythonw.exe"} for child in owned
    )
    with tempfile.TemporaryDirectory(prefix="codeharness-packaged-") as directory:
        (Path(directory) / "README.md").write_text(
            "# Real packaged fixture\nmarker=cedar-light\n", encoding="utf-8"
        )
        # trust_env=False: a proxy variable in the shell would send these loopback requests
        # to the proxy, which answers them 404, and the gate would fail for the wrong reason.
        with httpx.Client(
            base_url=f"http://127.0.0.1:{port}", timeout=60, trust_env=False
        ) as client:
            assert client.get("/health").status_code == 401
            client.headers["Authorization"] = "Bearer packaged-fixture-token"
            assert client.get("/health").status_code == 200
            presets = client.get("/presets").json()
            assert len(presets) == 5
            assert all(item["url"] is None for item in presets if item["name"] in {"Jev", "Metis"})
            assert client.get("/models").json()[0]["kind"] == "demo"
            assert client.get("/settings").json()["locale"] == "fa"
            response = client.post(
                "/runs",
                json={
                    "task": "read README.md and summarize",
                    "workspace": directory,
                    "model": "demo",
                },
            )
            assert response.status_code == 201
            run_id = response.json()["run_id"]
            stream = client.get(f"/runs/{run_id}/events").text
            events = [
                json.loads(line[6:])
                for line in stream.splitlines()
                if line.startswith("data:")
            ]
            assert (
                events[-1]["type"] == "run.finished"
                and events[-1]["status"] == "completed"
            )
            assert any(
                event["type"] == "tool.result" and "cedar-light" in event["text"]
                for event in events
            )
            assert "packaged-fixture-token" not in stream
    process.stdin.close()
    process.wait(timeout=5)
    _, alive = psutil.wait_procs(owned, timeout=5)
    assert not alive, "Packaged engine survived watchdog EOF"
    print(
        "Packaged engine: authenticated demo read, OpenUI stream, "
        "no Python child, clean watchdog shutdown."
    )
finally:
    if process.poll() is None:
        if process.stdin is not None and not process.stdin.closed:
            process.stdin.close()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            for child in owned:
                if child.is_running():
                    child.kill()
