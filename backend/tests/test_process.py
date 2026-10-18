import json
import os
import subprocess
import sys
from pathlib import Path

import httpx
import psutil


def test_plain_python_engine_bound_loopback_and_auth() -> None:
    env = {
        key: value
        for key, value in os.environ.items()
        if key in {"SystemRoot", "WINDIR", "PATH", "TEMP", "TMP", "USERPROFILE"}
    }
    env["PYTHONUTF8"] = "1"
    process = subprocess.Popen(
        [sys.executable, "-m", "server"],
        cwd=Path(__file__).resolve().parents[1],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env=env,
    )
    try:
        assert process.stdin is not None and process.stdout is not None
        process.stdin.write("process-canary-token\n")
        process.stdin.flush()
        port = json.loads(process.stdout.readline())["port"]
        connections = psutil.Process(process.pid).net_connections(kind="inet")
        assert any(item.laddr.ip == "127.0.0.1" and item.laddr.port == port for item in connections)
        assert all(item.laddr.ip == "127.0.0.1" for item in connections if item.status == "LISTEN")
        with httpx.Client(base_url=f"http://127.0.0.1:{port}") as client:
            assert client.get("/health").status_code == 401
            assert (
                client.get("/health", headers={"Authorization": "Bearer wrong"}).status_code == 401
            )
            assert (
                client.get(
                    "/health", headers={"Authorization": "Bearer process-canary-token"}
                ).status_code
                == 200
            )
    finally:
        process.kill()
        process.communicate(timeout=10)
