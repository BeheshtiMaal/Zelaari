from agent.events import MessageDelta, Protocol, event_adapter


def test_event_roundtrip_and_schema() -> None:
    event = MessageDelta(run_id="fixture", seq=1, message_id="answer", text="سلام")
    assert event_adapter.validate_json(event.model_dump_json()) == event
    assert event.ts.tzinfo is not None
    assert "discriminator" in Protocol.model_json_schema()["properties"]["event"]
