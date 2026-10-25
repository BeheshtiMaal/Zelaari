"""A minimal stdio MCP server for tests: initialize, tools/list, tools/call.

Usage: python mcp_worker.py <mode>
Modes: normal | silent | exit | broken
"""

import json
import sys
import time

TOOLS = [
    {
        "name": "echo",
        "description": "Echo the text back.",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "count",
        "description": "Count to a number.",
        "inputSchema": {
            "type": "object",
            "properties": {"limit": {"type": "integer"}},
        },
    },
]


def send(payload: dict[str, object]) -> None:
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "normal"
    if mode == "exit":
        return 0
    if mode == "silent":
        time.sleep(60)
        return 0
    for line in sys.stdin:
        try:
            message = json.loads(line)
        except ValueError:
            continue
        if not isinstance(message, dict) or "id" not in message:
            continue
        identifier = message["id"]
        method = message.get("method")
        if method == "initialize":
            if mode == "broken":
                send({"jsonrpc": "2.0", "id": identifier, "error": {"code": -1, "message": "no"}})
                continue
            send(
                {
                    "jsonrpc": "2.0",
                    "id": identifier,
                    "result": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "fixture", "version": "1.0.0"},
                    },
                }
            )
        elif method == "tools/list":
            send({"jsonrpc": "2.0", "id": identifier, "result": {"tools": TOOLS}})
        elif method == "tools/call":
            params = message.get("params") or {}
            arguments = params.get("arguments") or {}
            name = params.get("name")
            if name == "echo":
                text = f"echo: {arguments.get('text', '')}"
                send(
                    {
                        "jsonrpc": "2.0",
                        "id": identifier,
                        "result": {"content": [{"type": "text", "text": text}]},
                    }
                )
            elif name == "count":
                send(
                    {
                        "jsonrpc": "2.0",
                        "id": identifier,
                        "result": {
                            "content": [{"type": "text", "text": str(arguments.get("limit", 0))}]
                        },
                    }
                )
            else:
                send(
                    {
                        "jsonrpc": "2.0",
                        "id": identifier,
                        "result": {
                            "isError": True,
                            "content": [{"type": "text", "text": "unknown tool"}],
                        },
                    }
                )
        else:
            send(
                {
                    "jsonrpc": "2.0",
                    "id": identifier,
                    "error": {"code": -32601, "message": "unknown method"},
                }
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
