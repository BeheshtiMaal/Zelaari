"""Deliver queued human messages once at a checkpointed parent-only boundary."""

from typing import Annotated, Any, NotRequired

from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import AgentState, PrivateStateAttr
from langchain_core.messages import HumanMessage
from langgraph.runtime import Runtime

from agent.activity import identity
from store.steering import SteeringQueue


class SteeringState(AgentState[Any]):
    steering_seen: NotRequired[Annotated[list[str], PrivateStateAttr]]


class SteeringMiddleware(AgentMiddleware[SteeringState, Any, Any]):
    state_schema = SteeringState

    def __init__(self, queue: SteeringQueue) -> None:
        self.queue = queue

    async def abefore_model(
        self, state: SteeringState, runtime: Runtime[Any]
    ) -> dict[str, Any] | None:
        seen = list(state.get("steering_seen", []))
        pending = [record for record in self.queue.pending() if record.submission_id not in seen]
        if not pending:
            return None
        return {
            "messages": [
                HumanMessage(
                    id=identity(self.queue.run_id + record.submission_id), content=record.text
                )
                for record in pending
            ],
            "steering_seen": [*seen, *(record.submission_id for record in pending)],
        }
