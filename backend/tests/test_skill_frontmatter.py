"""Frontmatter is a small, explainable subset: valid, invalid, and never an exception."""


import pytest

from skills import frontmatter


def test_the_mocks_grill_me_file_parses() -> None:
    text = (
        "---\n"
        "name: grill-me\n"
        "description: Interview the user until\n"
        "  the task is fully specified\n"
        "command: /grill\n"
        "---\n"
        "Ask one batch of questions at a time.\n"
    )
    fields, problem = frontmatter.validate(frontmatter.split(text), "grill-me")
    assert problem is None
    assert fields == {
        "name": "grill-me",
        "description": "Interview the user until the task is fully specified",
        "command": "/grill",
        "category": "other",
        "requires_approval": False,
        "enabled": True,
        "body": "Ask one batch of questions at a time.",
    }


def test_boolean_keys_are_booleans() -> None:
    text = (
        "---\nname: web-search\ndescription: Search.\nrequires_approval: true\n"
        "enabled: false\ncategory: web\n---\nBody\n"
    )
    fields, problem = frontmatter.validate(frontmatter.split(text), "web-search")
    assert problem is None
    assert fields["requires_approval"] is True
    assert fields["enabled"] is False
    assert fields["category"] == "web"


@pytest.mark.parametrize(
    ("text", "folder", "expected"),
    [
        ("no frontmatter\n", "x", "must start with a --- frontmatter block"),
        ("---\nname: x\ndescription: d\n", "x", "frontmatter is not closed"),
        ("---\nname: X\ndescription: d\n---\n", "X", "name must be lowercase"),
        ("---\nname: other\ndescription: d\n---\n", "x", "does not match skill name"),
        ("---\nname: x\n---\n", "x", "description is required"),
        ("---\nname: x\ndescription: d\nnope: 1\n---\n", "x", "Unknown frontmatter key"),
        ("---\nname: x\ndescription: d\ncommand: grill\n---\n", "x", "command must look like"),
        ("---\nname: x\ndescription: d\ncategory: music\n---\n", "x", "category must be"),
        ("---\nname: x\ndescription: d\nenabled: maybe\n---\n", "x", "must be true or false"),
        ("---\nname: x\ndescription: d\nname: y\n---\n", "x", "Duplicate frontmatter key"),
    ],
)
def test_invalid_files_explain_themselves(text: str, folder: str, expected: str) -> None:
    fields, problem = frontmatter.validate(frontmatter.split(text), folder)
    assert fields == {}
    assert problem is not None and expected in problem


def test_description_length_is_bounded() -> None:
    text = f"---\nname: x\ndescription: {'a' * 1025}\n---\n"
    _, problem = frontmatter.validate(frontmatter.split(text), "x")
    assert problem is not None and "longer than 1024" in problem


def test_body_length_is_bounded() -> None:
    text = f"---\nname: x\ndescription: d\n---\n{'a' * 32_001}"
    _, problem = frontmatter.validate(frontmatter.split(text), "x")
    assert problem is not None and "body is longer" in problem


def test_comments_and_quotes_are_supported() -> None:
    text = '---\n# a comment\nname: "x"\ndescription: \'quoted\'\n---\n'
    fields, problem = frontmatter.validate(frontmatter.split(text), "x")
    assert problem is None
    assert (fields["name"], fields["description"]) == ("x", "quoted")


def test_render_round_trips() -> None:
    meta = {
        "name": "my-skill",
        "description": "Does one thing.",
        "command": "/mine",
        "category": "tests",
        "requires_approval": True,
        "enabled": False,
    }
    text = frontmatter.render(meta, "Body line\n")
    fields, problem = frontmatter.validate(frontmatter.split(text), "my-skill")
    assert problem is None
    assert fields["command"] == "/mine"
    assert fields["category"] == "tests"
    assert fields["requires_approval"] is True
    assert fields["enabled"] is False
    assert fields["body"] == "Body line"
