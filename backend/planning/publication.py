"""Reconcile accepted checkpoint state with its durable public plan history."""

from planning.types import PlanRecord
from store.eventlog import EventBus


async def publish_plan(bus: EventBus, plan: PlanRecord | None) -> None:
    if plan is None:
        return
    if plan.run_id != bus.run_id:
        raise ValueError("Plan belongs to another run")
    if plan.adoption not in {"automatic", "approved"}:
        return
    previous = next(
        (
            event.plan
            for event in reversed(bus.history)
            if event.type == "plan.created" and event.plan.plan_id == plan.plan_id
        ),
        None,
    )
    if previous is None or previous.revision != plan.revision:
        await bus.emit("plan.created", plan=plan)
        return
    progress = {item.step_id: item for item in previous.progress}
    for event in bus.history:
        if (
            event.type == "plan.step.updated"
            and event.plan_id == plan.plan_id
            and event.revision == plan.revision
        ):
            progress[event.progress.step_id] = event.progress
    for item in plan.progress:
        if progress.get(item.step_id) != item:
            await bus.emit(
                "plan.step.updated",
                plan_id=plan.plan_id,
                revision=plan.revision,
                progress=item,
            )
