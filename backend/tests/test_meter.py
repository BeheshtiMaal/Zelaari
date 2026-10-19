from langchain_core.messages import AIMessage, AIMessageChunk

from agent.meter import TokenMeter, content_parts


def test_actual_reasoning_only_and_structured_blocks() -> None:
    assert content_parts(AIMessage(content="answer")) == ("answer", "")
    assert content_parts(AIMessageChunk(content=[
        {"type": "thinking", "thinking": "real thought", "signature": "not displayed"},
        {"type": "text", "text": "answer"},
    ])) == ("answer", "real thought")
    assert content_parts(AIMessageChunk(content="answer", additional_kwargs={
        "reasoning_content": "provider reasoning"
    })) == ("answer", "provider reasoning")


def test_meter_uses_final_usage_once_and_marks_any_estimate() -> None:
    meter = TokenMeter(100)
    turn = AIMessage(content="answer", usage_metadata={
        "input_tokens": 50, "output_tokens": 10, "total_tokens": 60
    })
    assert meter.turn(turn, "turn-one")
    assert not meter.turn(turn, "turn-one")
    assert (meter.input_tokens, meter.output_tokens, meter.estimated) == (50, 10, False)
    assert meter.turn(AIMessage(content="next answer"), "turn-two")
    assert meter.input_tokens > 50 and meter.output_tokens > 10 and meter.estimated
