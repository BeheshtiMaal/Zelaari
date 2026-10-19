"""Subprocess fixture: force-kill a real engine at a mixed question barrier."""

import asyncio
import json
import sys
from pathlib import Path

from agent.bridge import RunManager
from agent.events import RunRequest
from permissions.types import ApprovalDecision
from questions.types import QuestionDecision
from store.catalog import Catalog


async def main() -> None:
    root, stage = Path(sys.argv[1]), sys.argv[2]
    manager = RunManager(catalog=Catalog(root.parent / "catalog.json"), demo_delay=0)
    if stage == "start":
        run_id = await manager.start(RunRequest(task="demo question mixed", workspace=str(root)))
        while not manager.questions(run_id) or not manager.approvals("pending"):
            await asyncio.sleep(0.01)
        record = manager.questions(run_id)[0]
        await manager.answer_question(
            run_id,
            record.request.call_id,
            QuestionDecision(interrupt_id=record.interrupt_id, status="declined"),
        )
        print(json.dumps({"ready": True, "run_id": run_id}), flush=True)
        await asyncio.Event().wait()
    else:
        await manager.recover()
        run_id = manager.catalog.data.workspaces.tasks[0].id
        while run_id not in manager.runs or not manager.runs[run_id].barrier:
            await asyncio.sleep(0.01)
        await manager.resolve(run_id, "demo-mixed-write", ApprovalDecision(decision="approve"))
        while not manager.runs[run_id].bus.finished:
            await asyncio.sleep(0.01)
        assert manager.questions(run_id)[0].status == "declined"
        await manager.close()


if __name__ == "__main__":
    asyncio.run(main())
