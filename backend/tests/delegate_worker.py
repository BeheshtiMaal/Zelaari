"""Force-kill fixture: retain a completed reviewer while a researcher is reading."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from deepagents.backends.protocol import ReadResult

from agent.activity import delegate_scope
from agent.bridge import RunManager
from agent.events import RunRequest
from permissions.types import ApprovalDecision
from planning.types import SteeringSubmission
from store.catalog import Catalog
from tools.fs import WorkspaceBackend


async def main() -> None:
    root, stage = Path(sys.argv[1]), sys.argv[2]
    manager = RunManager(catalog=Catalog(root.parent / "catalog.json"), demo_delay=0)
    if len(sys.argv) > 3 and sys.argv[3] == "plan":
        if stage == "start":
            run_id = await manager.start(
                RunRequest(task="demo planning risky small", workspace=str(root))
            )
            while not manager.approvals("pending"):
                await asyncio.sleep(0.01)
            await manager.steer(
                run_id, SteeringSubmission(submission_id="during-plan", text="Keep scope")
            )
            print(json.dumps({"run_id": run_id}), flush=True)
            await asyncio.Event().wait()
        else:
            await manager.recover()
            run_id = manager.catalog.data.workspaces.tasks[0].id
            while not manager.runs[run_id].barrier:
                await asyncio.sleep(0.01)
            await manager.resolve(run_id, "fixture-plan", ApprovalDecision(decision="approve"))
            await asyncio.wait_for(manager.runs[run_id].task, 60)
            events = manager.runs[run_id].bus.history
            assert events[-1].type == "run.finished" and events[-1].status == "completed"
            assert sum(e.type == "approval.requested" for e in events) == 1
            assert sum(e.type == "plan.created" for e in events) == 1
            steering = manager.runs[run_id].steering
            assert steering and steering.records[0].status == "delivered"
            await manager.close()
        return
    if stage == "start":
        original = WorkspaceBackend.aread
        entered = asyncio.Event()

        async def read(self: WorkspaceBackend, *args: Any, **kwargs: Any) -> ReadResult:
            scope = delegate_scope.get()
            if scope and scope.agent == "researcher":
                entered.set()
                await asyncio.Event().wait()
            return await original(self, *args, **kwargs)

        setattr(WorkspaceBackend, "aread", read)
        run_id = await manager.start(RunRequest(task="demo planning small", workspace=str(root)))
        await entered.wait()
        while not any(
            e.type == "subagent.finished" and e.scope.agent == "reviewer"
            for e in manager.runs[run_id].bus.history
        ):
            await asyncio.sleep(0.01)
        await manager.steer(
            run_id, SteeringSubmission(submission_id="during-delegate", text="Keep reads local")
        )
        print(json.dumps({"run_id": run_id}), flush=True)
        await asyncio.Event().wait()
    else:
        await manager.recover()
        run_id = manager.catalog.data.workspaces.tasks[0].id
        await asyncio.wait_for(manager.runs[run_id].task, 60)
        events = manager.runs[run_id].bus.history
        assert events[-1].type == "run.finished" and events[-1].status == "completed"
        assert (
            sum(e.type == "subagent.started" and e.scope.agent == "reviewer" for e in events) == 1
        )
        researcher = [
            e for e in events if e.type == "subagent.started" and e.scope.agent == "researcher"
        ]
        assert len(researcher) == 2
        assert researcher[0].scope.invocation_id == researcher[1].scope.invocation_id
        assert researcher[0].scope.scope_id != researcher[1].scope.scope_id
        assert any(e.type == "subagent.finished" and e.status == "interrupted" for e in events)
        steering = manager.runs[run_id].steering
        assert steering and steering.records[0].status == "delivered"
        await manager.close()


if __name__ == "__main__":
    asyncio.run(main())
