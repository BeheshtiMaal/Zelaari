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


def prepare(results: list[ToolMessage], content: str) -> AIMessage | None:
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
                        "expected_files": ["notes.txt"],
                    }
                ]
            },
            "verify-plan",
        )
    if "write_todos" not in kinds:
        todos = [{"content": "[change] Apply the requested change", "status": "in_progress"}]
        return call("write_todos", {"todos": todos}, "verify-progress")
    if "write_file" not in kinds:
        return call("write_file", {"file_path": "notes.txt", "content": content}, "verify-write")
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


def demo_verify(task: str, messages: list[Any], results: list[ToolMessage]) -> AIMessage | None:
    if not task.startswith("demo verify"):
        return None
    prompts = injected(messages)
    if task.startswith("demo verify question"):
        return asking(results, prompts)
    if task.startswith("demo verify fail"):
        return failing(results, prompts)
    return gate(results, prompts)
