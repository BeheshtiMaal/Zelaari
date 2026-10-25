"""Prove a packaged tree works: its own engine, its own sample, its own exit.

The tree is either an installed folder or `dist/win-unpacked`. Two halves:

1. The engine the app ships is driven directly with a known token, because the app's own
   token is generated in the Electron main process and never leaves it. This half proves
   the sample project resolves out of the bundle and that a demo task returns a real tool
   result.
2. The real `CodeHarness.exe` is launched, and the facts only it can show are asserted:
   the window comes up, its engine answers, no Python or Node runtime is present, and
   closing the window leaves no engine or watchdog behind.

Run: uv run --project backend python scripts/smoke-installer.py dist/win-unpacked
"""

from __future__ import annotations

import json
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import httpx
import psutil

TOKEN = "smoke-installer-token"
MARKER = "smoke-marker-cedar"
TASK = "read README.md and summarize"
RUNTIMES = {"python.exe", "pythonw.exe", "node.exe", "node"}
SECRET = re.compile(rb"\bsk-(?:ant-)?[A-Za-z0-9_\-]{20,}")
BEARER = re.compile(rb"Bearer\s+[0-9a-f]{16,}")


def engine_root(tree: Path) -> Path:
    """Where `build/engine` sits, installed (`resources/`) or unpacked from the repo."""
    for candidate in (tree / "resources" / "build" / "engine", tree / "build" / "engine"):
        if (candidate / "engine" / "engine.exe").is_file():
            return candidate
    raise SystemExit(f"No engine bundle under {tree}")


def child_environment() -> dict[str, str]:
    keep = {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATH", "USERPROFILE", "APPDATA", "LOCALAPPDATA"}
    environment = {name: value for name, value in os.environ.items() if name.upper() in keep}
    # A proxy variable in the shell turns loopback requests into proxy requests, and the
    # proxy answers them 404. Nothing here may depend on the ambient network settings.
    environment["NO_PROXY"] = "127.0.0.1,localhost"
    environment["no_proxy"] = "127.0.0.1,localhost"
    return environment


def check_bundle(bundle: Path, tree: Path) -> None:
    sample = bundle / "engine" / "examples" / "sample-project"
    assert (sample / "README.md").is_file(), f"The bundle has no sample project: {sample}"
    skill = sample / ".harness" / "skills" / "read-framework-docs" / "SKILL.md"
    assert skill.is_file(), f"The sample has no read-framework-docs skill: {skill}"

    found = {path.name.lower() for path in tree.rglob("*") if path.is_file()}
    shipped = found & RUNTIMES
    assert not shipped, f"A runtime is inside the packaged tree: {sorted(shipped)}"

    keys = [path for path in tree.rglob("*.key")]
    assert not keys, f"Key material inside the packaged tree: {keys}"
    for archive in tree.rglob("app.asar"):
        assert not SECRET.search(archive.read_bytes()), f"A model key is inside {archive.name}"


@contextmanager
def engine_session(bundle: Path, app_data: Path) -> Iterator[httpx.Client]:
    """The packaged watchdog and engine, with a token this script chose."""
    process = subprocess.Popen(
        [str(bundle / "watchdog" / "watchdog.exe"), str(bundle / "engine" / "engine.exe")],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env=child_environment(),
    )
    owned: list[psutil.Process] = []
    try:
        assert process.stdin is not None and process.stdout is not None
        process.stdin.write(json.dumps({"token": TOKEN, "app_data": str(app_data)}) + "\n")
        process.stdin.flush()
        lines: queue.Queue[str] = queue.Queue()
        threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True).start()
        announced = lines.get(timeout=60)
        assert announced, "The packaged engine announced no port"
        port = json.loads(announced)["port"]
        owned = psutil.Process(process.pid).children(recursive=True)
        assert any(child.name() == "engine.exe" for child in owned)
        assert not [child for child in owned if child.name().lower() in RUNTIMES], (
            "The packaged engine spawned a Python interpreter"
        )
        with httpx.Client(
            base_url=f"http://127.0.0.1:{port}", timeout=120, trust_env=False
        ) as client:
            yield client
    finally:
        if process.poll() is None:
            if process.stdin is not None and not process.stdin.closed:
                process.stdin.close()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                for child in owned:
                    if child.is_running():
                        child.kill()


def check_engine(client: httpx.Client, app_data: Path) -> None:
    assert client.get("/health").status_code == 401, "The engine answered without a token"
    client.headers["Authorization"] = f"Bearer {TOKEN}"
    assert client.get("/health").status_code == 200
    assert client.get("/health", headers={"Authorization": "Bearer wrong"}).status_code == 401

    opened = client.post("/workspaces/sample")
    assert opened.status_code == 200, f"Sample project did not open: {opened.text}"
    materialised = app_data / "sample-project"
    assert (materialised / "README.md").is_file(), "The sample was not copied into app data"
    skill = materialised / ".harness" / "skills" / "read-framework-docs" / "SKILL.md"
    assert skill.is_file(), "The sample's project skill was not copied"

    with tempfile.TemporaryDirectory(prefix="smoke-workspace-") as directory:
        workspace = Path(directory)
        (workspace / "README.md").write_text(f"# Smoke\nmarker={MARKER}\n", encoding="utf-8")
        created = client.post(
            "/runs", json={"task": TASK, "workspace": str(workspace), "model": "demo"}
        )
        assert created.status_code == 201, created.text
        stream = client.get(f"/runs/{created.json()['run_id']}/events").text
        events = [json.loads(line[6:]) for line in stream.splitlines() if line.startswith("data:")]
        assert events[-1]["type"] == "run.finished" and events[-1]["status"] == "completed"
        assert any(
            event["type"] == "tool.result" and MARKER in event["text"] for event in events
        ), "The demo run produced no real tool result"
        assert TOKEN not in stream, "The token leaked into the event stream"


def listening_port(app: psutil.Process) -> int | None:
    """The engine's port, read from the child that is actually listening."""
    for child in app.children(recursive=True):
        if child.name() != "engine.exe":
            continue
        for connection in child.net_connections(kind="inet"):
            if connection.status == psutil.CONN_LISTEN and connection.laddr:
                return int(connection.laddr.port)
    return None


def close_window(pid: int) -> None:
    import win32con
    import win32gui
    import win32process

    windows: list[int] = []

    def collect(hwnd: int, _: object) -> bool:
        _, owner = win32process.GetWindowThreadProcessId(hwnd)
        if owner == pid and win32gui.IsWindowVisible(hwnd):
            windows.append(hwnd)
        return True

    win32gui.EnumWindows(collect, None)
    assert windows, "The packaged app opened no visible window"
    for hwnd in windows:
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)


def check_application(tree: Path, app_data: Path) -> None:
    executable = next(tree.glob("*.exe"))
    environment = child_environment() | {"CODEHARNESS_TEST_USER_DATA": str(app_data)}
    process = subprocess.Popen([str(executable)], env=environment, cwd=str(tree))
    try:
        app = psutil.Process(process.pid)
        port = None
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline and port is None:
            port = listening_port(app)
            if port is None:
                time.sleep(0.5)
        assert port is not None, "The app's engine never started listening"
        base_url = f"http://127.0.0.1:{port}"
        with httpx.Client(base_url=base_url, timeout=30, trust_env=False) as client:
            answer = client.get("/health")
            assert answer.status_code == 401, "The app's engine answered unauthenticated"

        # Captured before the window closes: once the app is gone, its children cannot be
        # asked for, and a survivor is exactly what this check exists to find.
        owned = app.children(recursive=True)
        close_window(process.pid)
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            raise SystemExit("Closing the window did not quit the app") from None
        _, alive = psutil.wait_procs(owned, timeout=15)
        assert not alive, f"Processes outlived the app: {[child.name() for child in alive]}"

        log = app_data / "logs" / "main.log"
        if log.is_file():
            assert not BEARER.search(log.read_bytes()), "A bearer token was written to main.log"
    finally:
        if process.poll() is None:
            process.kill()


def main() -> None:
    tree = Path(sys.argv[1] if len(sys.argv) > 1 else "dist/win-unpacked").resolve()
    assert tree.is_dir(), f"Not a packaged tree: {tree}"
    bundle = engine_root(tree)
    check_bundle(bundle, tree)
    print(f"bundle: {bundle.relative_to(tree)} carries the sample, no runtime, no keys")

    with tempfile.TemporaryDirectory(prefix="smoke-engine-") as directory:
        engine_data = Path(directory)
        with engine_session(bundle, engine_data) as client:
            check_engine(client, engine_data)
    print("engine: token enforced, sample opened from the bundle, demo run read the file")

    with tempfile.TemporaryDirectory(prefix="smoke-app-") as directory:
        check_application(tree, Path(directory))
    print("app: window opened, engine answered, closed cleanly, no survivors")


if __name__ == "__main__":
    main()
