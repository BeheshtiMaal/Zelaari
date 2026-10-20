"""Offline Phase 6 walkthrough using actual plans, tools and delegated graphs."""

import json

from langchain_core.messages import AIMessage, ToolMessage


def demo_planning(task: str, results: list[ToolMessage]) -> AIMessage | None:
    if task.startswith("Read-only boundary probe"):
        if not results:
            return AIMessage(
                content="",
                tool_calls=[
                    {"name": "read_file", "id": "probe-read", "args": {"file_path": "README.md"}}
                ],
            )
        if len(results) == 1:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "write_file" if "write" in task else "run_command",
                        "id": "probe-forbidden",
                        "args": {
                            "file_path": "forbidden.txt",
                            "content": "must not write",
                            "command": "Write-Output forbidden",
                        },
                    }
                ],
            )
        return AIMessage(content="root = Callout(" + json.dumps(str(results[-1].content)) + ");")
    if task.startswith("demo plan revisions"):
        return demo_revisions(results)
    if not task.startswith("demo planning"):
        return None
    ids = {message.tool_call_id for message in results}
    titles = [
        "Read project context",
        "Review local source",
        "Write review notes",
        "Report findings",
    ]
    large = "small" not in task
    if not large:
        titles = titles[:2]

    def call(name: str, identity: str, args: dict[str, object]) -> AIMessage:
        return AIMessage(content="", tool_calls=[{"name": name, "id": identity, "args": args}])

    def progress(active: int) -> dict[str, object]:
        return {
            "todos": [
                {
                    "content": f"[s{n}] {title}",
                    "status": "completed"
                    if n < active
                    else "in_progress"
                    if n == active
                    else "pending",
                }
                for n, title in enumerate(titles)
            ]
        }

    if "fixture-plan" not in ids:
        return call(
            "submit_plan",
            "fixture-plan",
            {
                "steps": [
                    {
                        "id": f"s{n}",
                        "title": title,
                        "expected_files": ["README.md", "notes.txt"],
                        "high_risk": "risky" in task and n == 0,
                    }
                    for n, title in enumerate(titles)
                ]
            },
        )
    plan_result = next(m for m in results if m.tool_call_id == "fixture-plan")
    if "rejected" in str(plan_result.content).lower():
        return AIMessage(content='root = Callout("Plan rejected; no changes were made.");')
    if "fixture-start" not in ids:
        return call("write_todos", "fixture-start", progress(0))
    if "fixture-read" not in ids:
        message = call("read_file", "fixture-read", {"file_path": "README.md"})
        message.additional_kwargs["reasoning_content"] = (
            "I will read the local context before requesting independent reviews."
        )
        return message
    if "fixture-next" not in ids:
        return call("write_todos", "fixture-next", progress(1))
    if "fixture-reviewer" not in ids:
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "task",
                    "id": f"fixture-{name}",
                    "args": {
                        "subagent_type": name,
                        "description": (
                            "Read-only boundary probe: "
                            + ("write" if name == "reviewer" else "command")
                            if "forbidden" in task
                            else "Read README.md and report local findings."
                        ),
                    },
                }
                for name in ("reviewer", "researcher")
            ],
        )
    if large:
        if "fixture-write-start" not in ids:
            return call("write_todos", "fixture-write-start", progress(2))
        if "fixture-write" not in ids:
            return call(
                "write_file",
                "fixture-write",
                {
                    "file_path": "outside.txt" if "outside" in task else "notes.txt",
                    "content": "Reviewed local project context.\n",
                },
            )
        if "fixture-report" not in ids:
            return call("write_todos", "fixture-report", progress(3))
    if "fixture-complete" not in ids:
        return call("write_todos", "fixture-complete", progress(len(titles)))
    return AIMessage(
        content="root = Callout("
        + json.dumps("Planning walkthrough completed. Local findings are recorded above.")
        + ");"
    )


def demo_revisions(results: list[ToolMessage]) -> AIMessage:
    """Two automatic additions, reviewed third addition, then a reviewed drop."""
    ids = {message.tool_call_id for message in results}
    for count in range(2, 6):
        if f"revision-{count}" not in ids:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "submit_plan",
                        "id": f"revision-{count}",
                        "args": {
                            "steps": [{"id": f"s{n}", "title": f"Step {n}"} for n in range(count)]
                        },
                    }
                ],
            )
    if "revision-drop" not in ids:
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "submit_plan",
                    "id": "revision-drop",
                    "args": {"steps": [{"id": f"s{n}", "title": f"Step {n}"} for n in range(1, 4)]},
                }
            ],
        )
    return AIMessage(content='root = Callout("Plan revision decisions recorded.");')
