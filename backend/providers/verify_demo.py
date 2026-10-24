"""Offline Phase 7 walkthrough: the real gate, real commands, scripted decisions.

The model never asserts that its work is verified; it only decides what to do next. Every
blocking decision in these scenarios comes from the harness, exactly as with a real model.
"""

import json
import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

COMMAND = re.compile(r"`([^`]+)`")
VERIFICATION_HEADER = "Verification"
BROKEN = (
    'def parse_date(text):\n    raise ValueError("unsupported format")\n',
    'def parse_date(text):\n    return text.split("-")\n',
    'def parse_date(text):\n    return [int(part) for part in text.split("/")]\n',
)
FIXED = (
    "def parse_date(text):\n"
    '    year, month, day = (int(part) for part in text.split("-"))\n'
    "    return year, month, day\n"
)


def call(name: str, args: dict[str, Any], identifier: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "args": args, "id": identifier, "type": "tool_call"}],
    )


def injected(messages: list[Any]) -> list[str]:
    return [
        str(message.content)
        for message in messages
        if isinstance(message, HumanMessage)
        and message.additional_kwargs.get("harness") == "verify"
    ]


def marked(messages: list[Any], kind: str) -> list[str]:
    """Instructions the budget middleware injected, by kind."""
    return [
        str(message.content)
        for message in messages
        if isinstance(message, HumanMessage)
        and message.additional_kwargs.get("harness") == "budget"
        and message.additional_kwargs.get("kind") == kind
    ]


def exhausted_payload(content: str) -> dict[str, Any]:
    """The card the harness told the model to ask, copied verbatim."""
    start = content.find("{")
    if start < 0:
        return {}
    try:
        value, _ = json.JSONDecoder().raw_decode(content[start:])
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def names(results: list[ToolMessage]) -> list[str]:
    return [str(item.name) for item in results]


def asked_command(results: list[ToolMessage]) -> str | None:
    for item in reversed(results):
        if item.name != "ask_user_question":
            continue
        try:
            answer = json.loads(str(item.content))
        except ValueError:
            return None
        if not isinstance(answer, dict):
            return None
        for selection in answer.get("answers") or []:
            if not isinstance(selection, dict):
                continue
            other = selection.get("other")
            if isinstance(other, str) and other.strip():
                return other.strip()
            chosen = selection.get("option_ids") or []
            if chosen:
                return str(chosen[0]).replace("-", " ")
    return None


def verification_question() -> dict[str, Any]:
    return {
        "questions": [
            {
                "id": "verify",
                "header": VERIFICATION_HEADER,
                "text": "This project has no test command yet. How should I verify the change?",
                "type": "single",
                "options": [
                    {
                        "id": "pytest",
                        "label": "pytest -q",
                        "description": "Run the Python test suite.",
                    },
                    {
                        "id": "npm",
                        "label": "npm test",
                        "description": "Run the package test script.",
                    },
                ],
            }
        ]
    }


def prepare(
    results: list[ToolMessage], content: str, path: str = "notes.txt"
) -> AIMessage | None:
    """Read, then the accepted plan and active step a mutation needs (Phase 6 contract)."""
    kinds = names(results)
    if not results:
        return call("read_file", {"file_path": "README.md"}, "verify-read")
    if "submit_plan" not in kinds:
        return call(
            "submit_plan",
            {
                "steps": [
                    {
                        "id": "change",
                        "title": "Apply the requested change",
                        "expected_files": [path],
                    }
                ]
            },
            "verify-plan",
        )
    if "write_todos" not in kinds:
        todos = [{"content": "[change] Apply the requested change", "status": "in_progress"}]
        return call("write_todos", {"todos": todos}, "verify-progress")
    if "write_file" not in kinds:
        return call("write_file", {"file_path": path, "content": content}, "verify-write")
    return None


def run(prompts: list[str], kinds: list[str], index: int) -> AIMessage:
    found = COMMAND.search(prompts[-1])
    return call(
        "run_command",
        {"command": found.group(1) if found else "echo ok"},
        f"verify-run-{index}",
    )


def gate(results: list[ToolMessage], prompts: list[str]) -> AIMessage:
    prepared = prepare(results, "verified work\n")
    if prepared is not None:
        return prepared
    kinds = names(results)
    if prompts and "run_command" not in kinds:
        return run(prompts, kinds, 0)
    if "run_command" in kinds:
        return AIMessage(content="checks passed")
    # The model wants to finish without testing; the gate has to stop it.
    return AIMessage(content="done without checks")


def failing(results: list[ToolMessage], prompts: list[str]) -> AIMessage:
    prepared = prepare(results, "broken work\n")
    if prepared is not None:
        return prepared
    kinds = names(results)
    if prompts and kinds.count("run_command") < len(prompts):
        return run(prompts, kinds, kinds.count("run_command"))
    return AIMessage(content="still failing")


def asking(results: list[ToolMessage], prompts: list[str]) -> AIMessage:
    prepared = prepare(results, "verified work\n")
    if prepared is not None:
        return prepared
    kinds = names(results)
    if "ask_user_question" not in kinds:
        if prompts:
            return call("ask_user_question", verification_question(), "verify-question")
        return AIMessage(content="done without checks")
    command = asked_command(results)
    if command and "run_command" not in kinds:
        return call("run_command", {"command": command}, "verify-run")
    if "run_command" in kinds:
        return AIMessage(content="checks passed")
    return AIMessage(content="no command was chosen")


def exhausted_choice(results: list[ToolMessage]) -> str | None:
    for item in reversed(results):
        if item.name != "ask_user_question":
            continue
        try:
            answer = json.loads(str(item.content))
        except ValueError:
            continue
        if not isinstance(answer, dict):
            continue
        if answer.get("status") == "declined":
            return "stop"
        for selection in answer.get("answers") or []:
            if not isinstance(selection, dict):
                continue
            chosen = selection.get("option_ids") or []
            if chosen:
                return str(chosen[0])
            if selection.get("other"):
                return "retry"
    return None


def exhausted_hint(results: list[ToolMessage]) -> str:
    for item in reversed(results):
        if item.name != "ask_user_question":
            continue
        try:
            answer = json.loads(str(item.content))
        except ValueError:
            return ""
        if not isinstance(answer, dict):
            return ""
        for selection in answer.get("answers") or []:
            if not isinstance(selection, dict):
                continue
            hint = selection.get("hint") or selection.get("other")
            if isinstance(hint, str) and hint.strip():
                return hint.strip()
    return ""


def budget(results: list[ToolMessage], messages: list[Any], prompts: list[str]) -> AIMessage:
    """Three failing fix attempts, the exhausted card, then whatever the person chose."""
    ids = {item.tool_call_id for item in results}
    prepared = prepare(results, BROKEN[0], "parser.py")
    if prepared is not None:
        return prepared
    found = COMMAND.search(prompts[-1]) if prompts else None
    command = found.group(1) if found else "pytest -q"
    for index in range(len(BROKEN)):
        if f"verify-run-{index}" in ids:
            continue
        if index and f"verify-fix-{index}" not in ids:
            return call(
                "write_file",
                {"file_path": "parser.py", "content": BROKEN[index]},
                f"verify-fix-{index}",
            )
        return call("run_command", {"command": command}, f"verify-run-{index}")
    if "verify-question" not in ids:
        asked = marked(messages, "ask")
        if asked:
            return call("ask_user_question", exhausted_payload(asked[-1]), "verify-question")
        return AIMessage(content="out of attempts")
    choice = exhausted_choice(results)
    if choice in {"retry", "change"}:
        if choice == "change" and "verify-revision" not in ids:
            return call(
                "submit_plan",
                {
                    "steps": [
                        {
                            "id": "retry",
                            "title": "Retry the parser fix with a new approach",
                            "expected_files": ["parser.py"],
                        }
                    ]
                },
                "verify-revision",
            )
        if "verify-fix-final" not in ids:
            # The comment carries the person's guidance into the file, so a test can
            # prove the hint actually reached the model instead of only the card.
            guidance = exhausted_hint(results)
            content = f"# guidance: {guidance}\n{FIXED}" if guidance else FIXED
            return call(
                "write_file", {"file_path": "parser.py", "content": content}, "verify-fix-final"
            )
        if "verify-run-final" not in ids:
            return call("run_command", {"command": command}, "verify-run-final")
        return AIMessage(content="parser fixed")
    return AIMessage(content="stopped as asked; parser.py still raises")


def slow(results: list[ToolMessage], prompts: list[str]) -> AIMessage:
    """Keeps running a slow command until a budget stops the run."""
    prepared = prepare(results, "slow work\n")
    if prepared is not None:
        return prepared
    index = names(results).count("run_command")
    return call("run_command", {"command": "ping -n 8 127.0.0.1"}, f"verify-slow-{index}")


def hang(results: list[ToolMessage], prompts: list[str]) -> AIMessage:
    """One command that outlives a short deadline, then an unverified finish attempt."""
    prepared = prepare(results, "hanging work\n")
    if prepared is not None:
        return prepared
    if names(results).count("run_command") >= 1:
        return AIMessage(content="the command never answered")
    return call("run_command", {"command": "ping -n 20 127.0.0.1"}, "verify-hang-0")


def demo_verify(task: str, messages: list[Any], results: list[ToolMessage]) -> AIMessage | None:
    if not task.startswith("demo verify"):
        return None
    prompts = injected(messages)
    if task.startswith("demo verify slow"):
        return slow(results, prompts)
    if task.startswith("demo verify hang"):
        return hang(results, prompts)
    if task.startswith("demo verify question"):
        return asking(results, prompts)
    if task.startswith("demo verify fail"):
        return failing(results, prompts)
    if task.startswith("demo verify budget"):
        return budget(results, messages, prompts)
    return gate(results, prompts)
