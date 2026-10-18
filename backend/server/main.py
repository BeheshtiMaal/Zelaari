"""Bind once to an OS-assigned loopback port and announce that bound socket."""

import json
import os
import socket
import sys


def main() -> None:
    dev = "--dev" in sys.argv
    bootstrap = "" if dev else sys.stdin.readline().strip()
    token = bootstrap
    if bootstrap.startswith("{"):
        config = json.loads(bootstrap)
        token = str(config["token"])
        for key, value in config.get("provider", {}).items():
            if (
                key in {"CODEHARNESS_API_KEY", "CODEHARNESS_BASE_URL", "CODEHARNESS_MODEL"}
                and value
            ):
                os.environ[key] = str(value)
    if not token and not dev:
        raise SystemExit(2)
    for key in list(os.environ):
        if key.startswith(("LANGSMITH_", "LANGCHAIN_")):
            os.environ.pop(key, None)
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"

    import uvicorn

    from server.app import create_app

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(128)
        print(json.dumps({"port": listener.getsockname()[1]}), flush=True)
        uvicorn.Server(
            uvicorn.Config(create_app(token, dev=dev), log_level="critical", access_log=False)
        ).run(sockets=[listener])
