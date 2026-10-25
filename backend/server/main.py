"""Bind once to an OS-assigned loopback port and announce that bound socket."""

import json
import os
import socket
import sys
from collections.abc import Callable
from pathlib import Path


def hook_crashes(log: Callable[[str], None]) -> None:
    """Write the exception type and message, then let the default handler report it.

    Only the type and message: a traceback frame can hold the task text, and this file
    is meant to be safe to send.
    """
    previous = sys.excepthook

    def report(kind: type[BaseException], value: BaseException, traceback: object) -> None:
        log(f"unhandled {kind.__name__}: {value}")
        previous(kind, value, traceback)  # type: ignore[arg-type]

    sys.excepthook = report


def main() -> None:
    dev = "--dev" in sys.argv
    bootstrap = "" if dev else sys.stdin.readline().strip()
    token = bootstrap
    app_data: Path | None = None
    if bootstrap.startswith("{"):
        config = json.loads(bootstrap)
        token = str(config["token"])
        if config.get("app_data"):
            app_data = Path(config["app_data"])
    if not token and not dev:
        raise SystemExit(2)
    for key in list(os.environ):
        if key.startswith(("LANGSMITH_", "LANGCHAIN_")):
            os.environ.pop(key, None)
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"

    import uvicorn

    from server.app import create_app
    from server.logging import open_log

    # The same `logs` folder the Electron side writes `main.log` into, so the crash card's
    # "open the log folder" shows both halves of one failure.
    log = open_log(app_data / "logs") if app_data else (lambda message: None)
    hook_crashes(log)
    log(f"engine start mode={'dev' if dev else 'app'} pid={os.getpid()}")

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(128)
        port = listener.getsockname()[1]
        print(json.dumps({"port": port}), flush=True)
        log(f"engine listening port={port}")
        try:
            uvicorn.Server(
                uvicorn.Config(
                    create_app(token, dev=dev, app_data=app_data),
                    log_level="critical",
                    access_log=False,
                )
            ).run(sockets=[listener])
        finally:
            log("engine stop")
