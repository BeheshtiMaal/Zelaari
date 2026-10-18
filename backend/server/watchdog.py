"""A watchdog holding a kill-on-close job; Electron holds its stdin open.

Start the child suspended, assign the job, then resume it. Pipe EOF or the owner's
process handle closing ends the job, without polling potentially reused PIDs.
"""

import json
import subprocess
import sys
from collections.abc import Callable
from typing import cast

import pywintypes
import win32api
import win32con
import win32event
import win32file
import win32job
import win32pipe
import win32process


def wait_for_owner(bootstrap: str) -> None:
    """Watch the original process handle as well as pipe EOF.

    Chromium or debugger descendants may retain pipe handles after main dies;
    a handle to the original main process remains authoritative in that case.
    """
    parent_pid = json.loads(bootstrap).get("parent_pid") if bootstrap.startswith("{") else None
    if parent_pid is None:
        sys.stdin.read(1)
        return
    if not isinstance(parent_pid, int) or parent_pid <= 0:
        raise ValueError("Invalid owner process")
    owner = win32api.OpenProcess(win32con.SYNCHRONIZE, False, parent_pid)
    try:
        while win32event.WaitForSingleObject(owner, 100) == win32event.WAIT_TIMEOUT:
            try:
                win32pipe.PeekNamedPipe(win32api.GetStdHandle(-10), 0)
            except pywintypes.error as error:
                if error.winerror in {109, 232}:
                    return
                raise
    finally:
        win32api.CloseHandle(owner)


def main() -> None:
    executable = sys.argv[1]
    token = sys.stdin.readline()
    if not token.strip():
        raise SystemExit(2)
    # types-pywin32 312.0.0.20261006 wrongly declares this return as None.
    create_job = cast(Callable[[None, str], int], win32job.CreateJobObject)
    job = create_job(None, "")
    info = win32job.QueryInformationJobObject(job, win32job.JobObjectExtendedLimitInformation)
    info["BasicLimitInformation"]["LimitFlags"] = win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    win32job.SetInformationJobObject(job, win32job.JobObjectExtendedLimitInformation, info)
    security = pywintypes.SECURITY_ATTRIBUTES()
    security.bInheritHandle = True
    child_input, token_writer = win32pipe.CreatePipe(security, 0)
    win32api.SetHandleInformation(token_writer, 1, 0)
    startup = win32process.STARTUPINFO()
    startup.dwFlags = win32process.STARTF_USESTDHANDLES
    startup.hStdInput = child_input
    startup.hStdOutput = win32api.GetStdHandle(-11)  # Win32 STD_OUTPUT_HANDLE
    startup.hStdError = win32api.GetStdHandle(-12)  # Win32 STD_ERROR_HANDLE
    process, thread, _, _ = win32process.CreateProcess(
        None,
        subprocess.list2cmdline([executable, *sys.argv[2:]]),
        None,
        None,
        True,
        win32process.CREATE_SUSPENDED | win32process.CREATE_NO_WINDOW,
        None,
        None,
        startup,
    )
    try:
        win32job.AssignProcessToJobObject(job, process)
        win32process.ResumeThread(thread)
        win32file.WriteFile(token_writer, token.encode())
        win32api.CloseHandle(token_writer)
        win32api.CloseHandle(child_input)
        wait_for_owner(token)
    except BaseException:
        # Assignment failure must not leave a suspended, unowned process.
        win32api.TerminateProcess(process, 2)
        raise
    finally:
        win32api.CloseHandle(thread)
        win32api.CloseHandle(process)
        win32api.CloseHandle(job)


if __name__ == "__main__":
    main()
