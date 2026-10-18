"""A watchdog holding a kill-on-close job; Electron holds its stdin open.

Start the child suspended, assign the job, then resume it. EOF after Electron
death closes the job, terminating all descendants without polling parent PIDs.
"""

import subprocess
import sys
from collections.abc import Callable
from typing import cast

import pywintypes
import win32api
import win32file
import win32job
import win32pipe
import win32process


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
        subprocess.list2cmdline([executable]),
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
        sys.stdin.read(1)
    finally:
        win32api.CloseHandle(thread)
        win32api.CloseHandle(process)
        win32api.CloseHandle(job)


if __name__ == "__main__":
    main()
