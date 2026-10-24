"""`run_command`: PowerShell first, cmd fallback, bounded output, process-tree kill."""

import json
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from store.secrets import Redactor
from tools.env import child_environment, redact_environment
from tools.jail import JailError, resolve
from tools.types import CommandResult

DEFAULT_TIMEOUT = 120.0
MAX_TIMEOUT = 600.0
MAX_LINES = 200
MAX_CAPTURE_BYTES = 1_000_000


@dataclass(frozen=True)
class Shell:
    name: str
    executable: str
    prefix: tuple[str, ...]


def pick_shell(preference: str = "auto") -> Shell:
    """PowerShell when present, cmd otherwise. Never a bare string shell."""
    if preference != "cmd":
        for name in ("powershell.exe", "pwsh.exe"):
            found = shutil.which(name)
            if found:
                return Shell("powershell", found, ("-NoProfile", "-NonInteractive", "-Command"))
    comspec = shutil.which("cmd.exe") or "cmd.exe"
    return Shell("cmd", comspec, ("/d", "/s", "/c"))


class _BoundedReader(threading.Thread):
    """Drain the pipe so the child never blocks, but keep only a bounded prefix."""

    def __init__(self, stream: Any) -> None:
        super().__init__(daemon=True)
        self.stream = stream
        self.buffer = bytearray()
        self.overflow = False

    def run(self) -> None:
        while True:
            chunk = self.stream.read(8192)
            if not chunk:
                break
            if len(self.buffer) < MAX_CAPTURE_BYTES:
                room = MAX_CAPTURE_BYTES - len(self.buffer)
                self.buffer.extend(chunk[:room])
                if len(chunk) > room:
                    self.overflow = True
            else:
                self.overflow = True


class CommandRunner:
    def __init__(
        self,
        root: Path,
        redactor: Redactor,
        *,
        secrets: list[str] | None = None,
        shell: str = "auto",
        timeout: float = DEFAULT_TIMEOUT,
        max_lines: int = MAX_LINES,
    ) -> None:
        self.root = root
        self.redactor = redactor
        self.secrets = secrets or []
        # The workspace's terminal settings decide the shell, the deadline and the window;
        # a call may still ask for a longer timeout, up to the hard maximum.
        self.shell = shell
        self.timeout = float(timeout)
        self.max_lines = max(1, int(max_lines))
        self.cancelled = threading.Event()

    def cancel(self) -> None:
        """Signal owned command threads without blocking the event loop."""
        self.cancelled.set()

    def _cwd(self, value: str | None) -> Path:
        if value is None:
            return self.root
        resolved = resolve(self.root, value, allow_protected=True)
        if not resolved.path.is_dir():
            raise JailError("Working directory does not exist inside the workspace")
        return resolved.path

    def run(
        self,
        command: str,
        *,
        timeout: float | None = None,
        offset: int = 0,
        cwd: str | None = None,
    ) -> CommandResult:
        if self.cancelled.is_set():
            raise RuntimeError("Run was cancelled before command dispatch")
        shell = pick_shell(self.shell)
        working = self._cwd(cwd)
        limit = min(max(float(self.timeout if timeout is None else timeout), 1.0), MAX_TIMEOUT)
        environment = redact_environment(child_environment(self.secrets), self.secrets)

        argv = [shell.executable, *shell.prefix, command]
        started = time.monotonic()
        job: Any = None
        process: subprocess.Popen[bytes] | None = None
        killed = False
        timed_out = False
        try:
            creation = 0
            if sys.platform == "win32":
                from tools.jobobject import (
                    CREATE_NO_WINDOW,
                    CREATE_SUSPENDED,
                    JobObject,
                    resume_process,
                )

                creation = CREATE_SUSPENDED | CREATE_NO_WINDOW
                job = JobObject()

            process = subprocess.Popen(  # noqa: S603 - argv is built from a fixed shell and one string
                argv,
                cwd=str(working),
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=creation,
                start_new_session=sys.platform != "win32",
            )
            if job is not None:
                job.assign(process.pid)
                if not self.cancelled.is_set():
                    resume_process(process.pid)

            assert process.stdout is not None
            reader = _BoundedReader(process.stdout)
            reader.start()
            while process.poll() is None:
                if self.cancelled.is_set():
                    killed = self._kill(job, process)
                    break
                remaining = limit - (time.monotonic() - started)
                if remaining <= 0:
                    timed_out = True
                    killed = self._kill(job, process)
                    break
                try:
                    process.wait(timeout=min(remaining, 0.05))
                except subprocess.TimeoutExpired:
                    pass
            reader.join(timeout=5)
            raw = bytes(reader.buffer)
        finally:
            if job is not None:
                # Kill-on-close: any descendant still alive dies with the handle.
                if process is not None and process.poll() is None:
                    job.terminate()
                job.close()
            if process is not None and process.poll() is None:
                process.kill()
                process.wait(timeout=5)

        duration_ms = int((time.monotonic() - started) * 1000)
        text = self.redactor.text(raw.decode("utf-8", errors="replace"))
        return _window(
            command=command,
            shell=shell.name,
            text=text,
            offset=offset,
            exit_code=None if timed_out else process.returncode if process else None,
            duration_ms=duration_ms,
            timed_out=timed_out,
            timeout_seconds=limit,
            killed_tree=killed,
            overflow=reader.overflow,
            max_lines=self.max_lines,
        )

    @staticmethod
    def _kill(job: Any, process: subprocess.Popen[bytes]) -> bool:
        if job is not None:
            job.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            return True
        if sys.platform != "win32":
            import os
            import signal

            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                return True
            except OSError:
                process.kill()
                return False
        process.kill()
        return False


def _window(
    *,
    command: str,
    shell: str,
    text: str,
    offset: int,
    exit_code: int | None,
    duration_ms: int,
    timed_out: bool,
    timeout_seconds: float,
    killed_tree: bool,
    overflow: bool,
    max_lines: int = MAX_LINES,
) -> CommandResult:
    lines = text.splitlines()
    start = max(0, offset)
    window = lines[start : start + max_lines]
    remaining = max(0, len(lines) - start - len(window))
    body = "\n".join(window)
    if remaining:
        body += (
            f"\n... {remaining} more lines. "
            f"Call run_command again with offset={start + len(window)}."
        )
    if overflow:
        body += "\n... output exceeded the capture limit and was cut off."
    return CommandResult(
        command=command,
        shell=shell,  # type: ignore[arg-type]
        exit_code=exit_code,
        duration_ms=duration_ms,
        output=body,
        truncated=bool(remaining) or overflow,
        total_lines=len(lines),
        offset=start,
        timed_out=timed_out,
        timeout_seconds=timeout_seconds,
        killed_tree=killed_tree,
    )


class RunCommandInput(BaseModel):
    command: str = Field(description="The command line to run in the workspace root")
    timeout: float | None = Field(
        default=None,
        description=(
            "Seconds before the process tree is killed (the workspace default applies "
            "when omitted, max 600)"
        ),
    )
    offset: int = Field(default=0, description="Line offset for paging long output")


def build_run_command(runner: CommandRunner) -> StructuredTool:
    def run(command: str, timeout: float | None = None, offset: int = 0) -> str:
        result = runner.run(command, timeout=timeout, offset=offset)
        return json.dumps(result.model_dump(), ensure_ascii=False)

    return StructuredTool.from_function(
        func=run,
        name="run_command",
        description=(
            "Run a shell command in the workspace. PowerShell by default, cmd as fallback. "
            "Returns exit code and a bounded number of lines; page with offset. "
            "The whole process tree is killed when the timeout expires."
        ),
        args_schema=RunCommandInput,
    )
