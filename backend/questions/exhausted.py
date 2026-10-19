"""Phase 7 integration: question payload and stable exhaustion choices, no fix loop."""

from questions.types import QuestionInput


def exhausted_question(attempts: int, step: str, check: str, output: str) -> QuestionInput:
    if attempts < 1 or not step.strip() or not check.strip():
        raise ValueError("Exhaustion requires real failure context")
    return QuestionInput.model_validate(
        {
            "presentation": "exhausted",
            "failure": {
                "attempts": attempts,
                "step": step,
                "check": check,
                "output": output[:10000],
            },
            "questions": [
                {
                    "id": "exhausted",
                    "header": "Recovery",
                    "text": f"{check} is still failing. What should I do?",
                    "type": "single",
                    "options": [
                        {
                            "id": "retry",
                            "label": "Retry with a hint",
                            "description": "Provide guidance for another attempt.",
                        },
                        {
                            "id": "change",
                            "label": "Change approach",
                            "description": "Reconsider the approach from this step.",
                        },
                        {
                            "id": "stop",
                            "label": "Stop and report",
                            "description": "Keep approved changes; report the remaining failure.",
                        },
                    ],
                }
            ],
        }
    )
