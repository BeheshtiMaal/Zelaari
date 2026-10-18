"""Integration tests launch Electron and the actual PyInstaller output."""

import json
import os
import queue
import secrets
import subprocess
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import TextIO

import httpx
import psutil
import pytest

ROOT = Path(__file__).resolve().parents[2]


def read_lines(stream: TextIO, output: queue.Queue[str]) -> None:
    for line in stream:
        output.put(line)


@pytest.fixture
def launch() -> Iterator[tuple[subprocess.Popen[str], str, int, queue.Queue[str]]]:
    electron = ROOT / "ui/node_modules/electron/dist/electron.exe"
    assert electron.is_file(), "Install UI dependencies first"
    assert (ROOT / "python/dist/sidecar/sidecar.exe").is_file(), "Build onedir first"
    token = secrets.token_urlsafe(32)
    proc = subprocess.Popen(
        [str(electron), str(ROOT / "ui/electron/sidecar.cjs")],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={
            **{
                k: v
                for k, v in os.environ.items()
                if k.upper()
                in {
                    "SYSTEMROOT",
                    "PATH",
                    "TEMP",
                    "TMP",
                    "APPDATA",
                    "LOCALAPPDATA",
                    "USERPROFILE",
                    "COMSPEC",
                    "PATHEXT",
                }
            },
            "SPIKE_TOKEN": token,
        },
    )
    assert proc.stdin and proc.stdout and proc.stderr
    lines: queue.Queue[str] = queue.Queue()
    errors: queue.Queue[str] = queue.Queue()
    threading.Thread(target=read_lines, args=(proc.stdout, lines), daemon=True).start()
    threading.Thread(target=read_lines, args=(proc.stderr, errors), daemon=True).start()
    owned: list[psutil.Process] = []
    try:
        announcement = lines.get(timeout=30)
        # Electron itself writes a blank stdout line. The launcher validates
        # the sidecar's first stdout line before forwarding its port record.
        while not announcement.strip():
            try:
                announcement = lines.get(timeout=30)
            except queue.Empty:
                diagnostic = "".join(list(errors.queue)).replace(token, "[REDACTED]")
                raise AssertionError(
                    f"No handshake; exit={proc.poll()}; stderr={diagnostic}"
                ) from None
        assert token not in announcement
        record = json.loads(announcement)
        assert record["first_stdout_line"] is True
        port = int(record["port"])
        deadline = time.monotonic() + 30
        while True:
            try:
                response = httpx.get(
                    f"http://127.0.0.1:{port}/health",
                    headers={"Authorization": "Bearer " + token},
                    timeout=1,
                )
                if response.status_code == 200:
                    break
            except httpx.TransportError:
                pass
            assert time.monotonic() < deadline, "Health startup deadline exceeded"
            time.sleep(0.05)
        owned = psutil.Process(proc.pid).children(recursive=True)
        yield proc, token, port, lines
    finally:
        # Emergency cleanup is after all lifecycle assertions, never before them.
        try:
            parent = psutil.Process(proc.pid)
            descendants = parent.children(recursive=True)
            parent.kill()
            for child in descendants:
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
        except psutil.NoSuchProcess:
            pass
        for child in owned:
            try:
                if child.is_running():
                    child.kill()
            except psutil.NoSuchProcess:
                pass
        proc.wait(timeout=10)
        leaked = token in "".join(list(errors.queue))
        assert not leaked, "Token leaked to stderr"


@pytest.mark.parametrize("force", [False, True])
def test_packaged_electron_lifetime(
    launch: tuple[subprocess.Popen[str], str, int, queue.Queue[str]],
    force: bool,
) -> None:
    proc, token, port, lines = launch
    url = f"http://127.0.0.1:{port}/health"
    assert httpx.get(url).status_code == 401
    assert httpx.get(url, headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert httpx.get(url, headers={"Authorization": "Bearer " + token}).status_code == 200
    children = psutil.Process(proc.pid).children(recursive=True)
    engines = [p for p in children if p.name() == "sidecar.exe"]
    owned = [p for p in children if p.name() in {"sidecar.exe", "python.exe"}]
    assert len(engines) >= 2, "Must observe engine and its descendant"
    connections = [c for p in engines for c in p.net_connections(kind="inet")]
    assert any(c.laddr and c.laddr.ip == "127.0.0.1" and c.laddr.port == port for c in connections)
    assert all(not c.laddr or c.laddr.ip == "127.0.0.1" for c in connections)
    assert all(token not in " ".join(p.cmdline()) for p in children)
    if force:
        proc.kill()  # Only Electron main; the job must kill its own descendants.
    else:
        # Authenticated fixture route asks Electron to call app.quit().
        # Response may be cut short when the job closes immediately.
        try:
            httpx.post(
                url.replace("/health", "/quit"),
                headers={"Authorization": "Bearer " + token},
                timeout=2,
            )
        except httpx.TransportError:
            pass
    deadline = time.monotonic() + 5
    while any(p.is_running() for p in owned) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert all(not p.is_running() for p in owned)
    proc.wait(timeout=5)
    captured = "".join(list(lines.queue))
    assert token not in captured


def test_watchdog_start_failure() -> None:
    import sys

    token = secrets.token_urlsafe(32)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "python/job_launcher.py"),
            str(ROOT / "python/dist/missing-fixture.exe"),
        ],
        input=token + "\n",
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode != 0
    assert token not in result.stdout + result.stderr


def test_health_without_electron() -> None:
    from fastapi.testclient import TestClient

    from sidecar import create_app

    token = secrets.token_urlsafe(32)
    client = TestClient(create_app(token))
    assert client.get("/health").status_code == 401
    assert client.get("/health", headers={"Authorization": "Bearer " + token}).json() == {
        "status": "ok"
    }
