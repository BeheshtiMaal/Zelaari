"""The engine log has to be safe to send: bounded, rotated, and redacted."""

from datetime import UTC, datetime
from pathlib import Path

from server.logging import MAX_LINE, open_log, record, redact

MOMENT = datetime(2026, 10, 25, 10, 0, 0, tzinfo=UTC)


def test_a_record_is_one_line_with_a_utc_stamp() -> None:
    assert record("engine start pid=42", now=MOMENT) == "2026-10-25T10:00:00Z engine start pid=42\n"


def test_a_newline_in_a_message_cannot_forge_a_second_record() -> None:
    line = record("start\n2026-01-01T00:00:00Z engine stop", now=MOMENT)
    assert line.count("\n") == 1


def test_a_long_message_is_bounded() -> None:
    line = record("x" * 5000, now=MOMENT)
    assert len(line) <= MAX_LINE + 22


def test_an_api_key_is_removed() -> None:
    assert "sk-abc" not in redact("provider failed with sk-abcdefghijklmnop")
    assert "sk-***" in redact("provider failed with sk-abcdefghijklmnop")


def test_a_bearer_token_is_removed() -> None:
    text = redact("sent with Bearer eyJhbGciOiJIUzI1NiJ9.payload")
    assert "eyJhbGciOiJIUzI1NiJ9" not in text
    assert "Bearer ***" in text


def test_an_authorization_header_loses_its_value() -> None:
    # The named-secret rule runs first here, so the header value goes as a whole.
    text = redact("Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payload")
    assert "eyJhbGciOiJIUzI1NiJ9" not in text
    assert "Authorization=***" in text


def test_named_secrets_are_removed_whatever_the_case() -> None:
    for line in ("api_key=abc123", "API-KEY: abc123", "token=abc123", "Password = abc123"):
        assert "abc123" not in redact(line), line


def test_a_long_hex_run_is_treated_as_a_token() -> None:
    secret = "0123456789abcdef0123456789abcdef"
    assert secret not in redact(f"session {secret} opened")
    assert "***" in redact(f"session {secret} opened")


def test_ordinary_words_are_left_alone() -> None:
    text = redact("engine listening port=52341 mode=app")
    assert text == "engine listening port=52341 mode=app"


def test_the_file_never_grows_past_the_cap(tmp_path: Path) -> None:
    write = open_log(tmp_path, max_bytes=2048)
    for index in range(200):
        write(f"line {index} " + "y" * 100)
    log = tmp_path / "engine.log"
    assert log.stat().st_size <= 2048
    assert (tmp_path / "engine.log.1").exists(), "the cap has to rotate, not truncate in place"


def test_only_one_rotation_is_kept(tmp_path: Path) -> None:
    write = open_log(tmp_path, max_bytes=1024)
    for index in range(400):
        write(f"line {index} " + "z" * 60)
    assert sorted(path.name for path in tmp_path.iterdir()) == ["engine.log", "engine.log.1"]


def test_the_newest_lines_survive_in_the_live_file(tmp_path: Path) -> None:
    write = open_log(tmp_path, max_bytes=1024)
    for index in range(400):
        write(f"line {index} " + "z" * 60)
    assert "line 399" in (tmp_path / "engine.log").read_text(encoding="utf-8")


def test_a_write_that_cannot_happen_does_not_raise(tmp_path: Path) -> None:
    blocked = tmp_path / "logs"
    blocked.write_text("not a directory", encoding="utf-8")
    open_log(blocked)("engine start")  # must not raise


def test_a_task_body_never_reaches_the_file(tmp_path: Path) -> None:
    # The logger takes lifecycle messages; the redactor is the second line of defence for
    # the one case that could leak, a key pasted into a start-up error.
    write = open_log(tmp_path)
    write("engine start failed: api_key=sk-live-abcdefghijklmnop")
    text = (tmp_path / "engine.log").read_text(encoding="utf-8")
    assert "sk-live-abcdefghijklmnop" not in text
