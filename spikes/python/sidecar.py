"""Packaged loopback experiment. Token arrives through stdin, never argv/environment."""

import json
import secrets
import socket
import subprocess
import sys
from typing import Annotated

import uvicorn
from fastapi import FastAPI, Header, HTTPException


def create_app(token: str) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/health")
    def health(authorization: Annotated[str | None, Header()] = None) -> dict[str, str]:
        if not secrets.compare_digest(authorization or "", "Bearer " + token):
            raise HTTPException(status_code=401)
        return {"status": "ok"}

    @app.post("/quit")
    def quit_app(authorization: Annotated[str | None, Header()] = None) -> dict[str, str]:
        health(authorization)
        print(json.dumps({"quit": True}), flush=True)
        return {"status": "quitting"}

    return app


def main() -> None:
    if "--descendant" in sys.argv:
        import time

        time.sleep(300)
        return
    token = sys.stdin.readline().strip()
    if not token:
        raise SystemExit(2)
    # Descendant is intentionally not cleaned up here: the Windows job owns it.
    subprocess.Popen([sys.executable, "--descendant"], stdin=subprocess.DEVNULL)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(128)
        print(json.dumps({"port": listener.getsockname()[1]}), flush=True)
        uvicorn.Server(
            uvicorn.Config(create_app(token), log_level="critical", access_log=False)
        ).run(sockets=[listener])


if __name__ == "__main__":
    main()
