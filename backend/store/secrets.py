"""Redaction before persistence or rendering, including split stream tokens."""

import os


class Redactor:
    def __init__(self, values: list[str] | None = None) -> None:
        self.values = sorted(
            {
                value
                for value in [*(values or []), os.environ.get("CODEHARNESS_API_KEY", "")]
                if value
            },
            key=len,
            reverse=True,
        )

    def text(self, value: str) -> str:
        for secret in self.values:
            value = value.replace(secret, "[REDACTED]")
        return value


class StreamRedactor:
    """Hold a possible secret prefix until subsequent chunks disambiguate it."""

    def __init__(self, redactor: Redactor) -> None:
        self.redactor = redactor
        self.pending = ""

    def push(self, chunk: str, *, final: bool = False) -> str:
        self.pending = self.redactor.text(self.pending + chunk)
        keep = 0
        if not final:
            for secret in self.redactor.values:
                for length in range(1, min(len(secret), len(self.pending) + 1)):
                    if self.pending.endswith(secret[:length]):
                        keep = max(keep, length)
        split = len(self.pending) - keep
        ready, self.pending = self.pending[:split], self.pending[split:]
        return ready
