import json
import os
import subprocess
import sys
import time
from pathlib import Path

import psutil
import pytest
from deepagents.backends import LocalShellBackend


@pytest.mark.parametrize("shell", ["cmd", "powershell"])
def test_stock_windows_shell(tmp_path: Path, shell: str) -> None:
    backend = LocalShellBackend(
        root_dir=tmp_path,
        inherit_env=False,
        env={
            k: v
            for k, v in os.environ.items()
            if k.upper()
            in {
                "SYSTEMROOT",
                "PATH",
                "TEMP",
                "TMP",
                "COMSPEC",
                "PATHEXT",
            }
        },
    )

    def command(text: str) -> str:
        if shell == "powershell":
            return subprocess.list2cmdline(["powershell.exe", "-NoProfile", "-Command", text])
        return "cmd.exe /d /c " + text

    assert "fixture-output" in backend.execute(command("echo fixture-output")).output
    assert backend.execute(command("exit 7")).exit_code == 7
    fixture = tmp_path / "descendant.py"
    pidfile = tmp_path / "child.pid"
    fixture.write_text(
        "import subprocess,sys,time,pathlib\n"
        "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(20)'],"
        "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\n"
        f"pathlib.Path({str(pidfile)!r}).write_text(str(p.pid))\n"
        "time.sleep(4)\n",
        encoding="utf8",
    )
    invocation = subprocess.list2cmdline([sys.executable, str(fixture)])
    if shell == "powershell":
        invocation = "& '" + sys.executable + "' '" + str(fixture) + "'"
    started = time.monotonic()
    response = backend.execute(command(invocation), timeout=1)
    elapsed = time.monotonic() - started
    try:
        assert response.exit_code == 124
        assert pidfile.exists(), "Child fixture did not start before timeout"
        child = psutil.Process(int(pidfile.read_text()))
        survived = child.is_running()
        output = Path(__file__).resolve().parents[2] / "artifacts"
        output.mkdir(exist_ok=True)
        (output / f"shell-{shell}.json").write_text(
            json.dumps(
                {
                    "shell": shell,
                    "exit_code": response.exit_code,
                    "elapsed_seconds": elapsed,
                    "descendant_survived": survived,
                    "suitable_for_product": not survived and elapsed < 3,
                },
                indent=2,
            ),
            encoding="utf8",
        )
        # This is an empirical characterization, not a claim of safe cleanup.
        assert isinstance(survived, bool)
    finally:
        if pidfile.exists():
            try:
                psutil.Process(int(pidfile.read_text())).kill()
            except psutil.NoSuchProcess:
                pass
