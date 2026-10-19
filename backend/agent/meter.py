"""Per-turn accounting and extraction of actual provider content."""

import math

from langchain_core.messages import AIMessage, AIMessageChunk


def content_parts(message: AIMessage | AIMessageChunk) -> tuple[str, str]:
    text = ""
    reasoning = ""
    if isinstance(message.content, str):
        text = message.content
    else:
        for block in message.content:
            if isinstance(block, str):
                text += block
            elif isinstance(block, dict):
                if block.get("type") == "text":
                    value = block.get("text", "")
                    if isinstance(value, str):
                        text += value
                elif block.get("type") in {"thinking", "reasoning"}:
                    value = block.get("thinking", block.get("reasoning", ""))
                    if isinstance(value, str):
                        reasoning += value
    extra = message.additional_kwargs.get("reasoning_content")
    if isinstance(extra, str) and not reasoning:
        reasoning = extra
    return text, reasoning


class TokenMeter:
    def __init__(self, input_characters: int) -> None:
        self.input_characters = input_characters
        self.input_tokens = 0
        self.output_tokens = 0
        self.estimated = False
        self.seen: set[str] = set()

    def turn(self, message: AIMessage, identifier: str) -> bool:
        if identifier in self.seen:
            return False
        self.seen.add(identifier)
        text, reasoning = content_parts(message)
        output_size = len(text) + len(reasoning) + len(str(message.tool_calls))
        if message.usage_metadata:
            self.input_tokens += message.usage_metadata["input_tokens"]
            self.output_tokens += message.usage_metadata["output_tokens"]
        else:
            self.input_tokens += max(1, math.ceil(self.input_characters / 4))
            self.output_tokens += max(1, math.ceil(output_size / 4))
            self.estimated = True
        self.input_characters += output_size
        return True
