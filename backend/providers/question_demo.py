"""Offline scripted question consumers using the actual tool and graph barriers."""

import json
import re

from langchain_core.messages import AIMessage, ToolMessage

from questions.exhausted import exhausted_question


def sample_question(
    kind: str = "single", identifier: str = "approach", locale: str = "en"
) -> dict[str, object]:
    if locale == "fa":
        return {
            "id": identifier,
            "header": "رویکرد",
            "text": "اگر ورودی تاریخ شمسی بود، چه کنم؟",
            "type": kind,
            "options": [
                {
                    "id": "small",
                    "label": "تبدیل به میلادی",
                    "description": "یک تابع کمکی اضافه می‌شود و تست جدید می‌نویسم.",
                },
                {
                    "id": "refactor",
                    "label": "خطای واضح بده",
                    "description": "فقط قالب میلادی پشتیبانی می‌شود.",
                },
            ],
        }
    return {
        "id": identifier,
        "header": "Approach",
        "text": "How should this task proceed?",
        "type": kind,
        "options": [
            {
                "id": "small",
                "label": "Small focused change",
                "description": "Keep the current structure and add focused checks.",
            },
            {
                "id": "refactor",
                "label": "Refactor first",
                "description": "Improve structure before implementing the change.",
            },
        ],
    }


def demo_question(task: str, results: list[ToolMessage], locale: str = "en") -> AIMessage | None:
    grill = bool(re.match(r"^/grill(?:\s|$)", task))
    if not grill and not task.startswith("demo question"):
        return None
    answers = [item for item in results if item.name == "ask_user_question"]
    if answers and json.loads(str(answers[-1].content)).get("status") == "declined":
        return AIMessage(
            content='root = Callout("Interview declined. No implementation started.");'
            if grill
            else 'root = Callout("Question declined. Recorded permissions still apply.");'
        )
    if grill:
        if len(answers) < 2:
            q = sample_question(identifier="scope" if answers else "objective")
            q["text"] = (
                "What outcome matters most?" if not answers else "How should success be checked?"
            )
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "ask_user_question",
                        "args": {"questions": [q]},
                        "id": f"grill-{len(answers)}",
                    }
                ],
            )
        if not any(item.name == "finish_interview" for item in results):
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "finish_interview",
                        "id": "ready",
                        "args": {
                            "objective": task.removeprefix("/grill").strip()
                            or "Clarify the requested task",
                            "scope": "Use the supplied interview answers: "
                            + str(answers[0].content)[:300],
                            "constraints": "Preserve existing permissions and approved scope.",
                            "acceptance": "Apply the selected success criteria: "
                            + str(answers[1].content)[:300],
                        },
                    }
                ],
            )
        return AIMessage(
            content='root = Callout("Interview complete. The task summary is recorded.");'
        )
    if not answers:
        kind = next((kind for kind in ("multi", "rank") if kind in task), "single")
        args = (
            exhausted_question(
                3, "Demo recovery", "demo check", "Fixture failure output"
            ).model_dump()
            if "exhausted" in task
            else {"questions": [sample_question(kind, locale=locale)]}
        )
        if "batch" in task:
            args = {
                "questions": [sample_question(kind, kind) for kind in ("single", "multi", "rank")]
            }
        calls = [{"name": "ask_user_question", "args": args, "id": "demo-question"}]
        if "mixed" in task:
            calls.append(
                {
                    "name": "write_file",
                    "args": {"file_path": "demo-answer.txt", "content": "Approved mixed effect\n"},
                    "id": "demo-mixed-write",
                }
            )
        return AIMessage(content="", tool_calls=calls)
    payload = json.loads(str(answers[-1].content))
    selected = payload.get("answers", [])
    stopped = any("stop" in item["option_ids"] for item in selected)
    text = (
        "Stopped and reported. Approved changes remain."
        if stopped
        else "Structured answer received: " + str(answers[-1].content)
    )
    return AIMessage(content=f"root = Callout({json.dumps(text)});")
