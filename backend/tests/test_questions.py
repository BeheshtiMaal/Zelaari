"""Question schema boundaries and exact answer validation."""

from typing import Any

import pytest

from questions.types import Question, QuestionAnswer, QuestionInput, QuestionRequest


def question(kind: str = "single") -> dict[str, Any]:
    return {
        "id": "q",
        "header": "Approach",
        "text": "Which approach?",
        "type": kind,
        "options": [{"id": key, "label": key, "description": "Description"} for key in ("a", "b")],
    }


def test_question_boundaries() -> None:
    for count in (1, 3):
        QuestionInput.model_validate(
            {"questions": [{**question(), "id": f"q{i}"} for i in range(count)]}
        )
    for questions in ([], [question()] * 4, [question()] * 2):
        with pytest.raises(ValueError):
            QuestionInput.model_validate({"questions": questions})
    patches: list[dict[str, Any]] = [
        {"header": " "},
        {"header": "h" * 41},
        {"text": "t" * 4001},
        {"type": "bad"},
        {"id": "../q"},
        {"options": []},
        {"options": question()["options"] * 2},
    ]
    for patch in patches:
        with pytest.raises(ValueError):
            Question.model_validate({**question(), **patch})


@pytest.mark.parametrize(
    "kind,ids,other,valid",
    [
        ("single", ["a"], None, True),
        ("single", [], "custom", True),
        ("single", ["a"], "custom", False),
        ("single", [], None, False),
        ("multi", ["b", "a"], "custom", True),
        ("multi", [], "custom", True),
        ("multi", [], None, False),
        ("multi", ["a", "a"], None, False),
        ("single", ["unknown"], None, False),
        ("single", [], "  ", False),
        ("rank", ["b", "a"], "custom", True),
        ("rank", ["b"], None, False),
    ],
)
def test_answer_types(kind: str, ids: list[str], other: str | None, valid: bool) -> None:
    request = QuestionRequest.model_validate(
        {"run_id": "run", "call_id": "call", "questions": [question(kind)]}
    )
    answer = QuestionAnswer.model_validate(
        {
            "run_id": "run",
            "call_id": "call",
            "interrupt_id": "graph",
            "status": "answered",
            "answers": [{"question_id": "q", "option_ids": ids, "other": other}],
        }
    )
    if valid:
        answer.validate_request(request)
    else:
        with pytest.raises(ValueError):
            answer.validate_request(request)


def test_declined_and_wrong_identity() -> None:
    request = QuestionRequest.model_validate(
        {"run_id": "run", "call_id": "call", "questions": [question()]}
    )
    answer = QuestionAnswer(run_id="run", call_id="call", interrupt_id="graph", status="declined")
    answer.validate_request(request)
    with pytest.raises(ValueError):
        answer.model_copy(update={"run_id": "other"}).validate_request(request)


def test_option_and_answer_boundaries() -> None:
    for count in (2, 4):
        payload = {
            **question(),
            "options": [
                {"id": f"o{i}", "label": "Option", "description": "Detail"} for i in range(count)
            ],
        }
        Question.model_validate(payload)
    for count in (1, 5):
        with pytest.raises(ValueError):
            Question.model_validate(
                {
                    **question(),
                    "options": [
                        {"id": f"o{i}", "label": "Option", "description": "Detail"}
                        for i in range(count)
                    ],
                }
            )
    request = QuestionRequest.model_validate(
        {"run_id": "run", "call_id": "call", "questions": [question()]}
    )
    for selections in (
        [],
        [{"question_id": "wrong", "option_ids": ["a"]}],
        [{"question_id": "q", "option_ids": ["a"]}] * 2,
    ):
        answer = QuestionAnswer.model_validate(
            {
                "run_id": "run",
                "call_id": "call",
                "interrupt_id": "graph",
                "status": "answered",
                "answers": selections,
            }
        )
        with pytest.raises(ValueError):
            answer.validate_request(request)
