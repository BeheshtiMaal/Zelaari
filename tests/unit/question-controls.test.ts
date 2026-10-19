import assert from "node:assert/strict";
import { test } from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { RegisteredQuestionCard } from "../../src/components/questions/question-card";
import { useQuestionStore } from "../../src/lib/use-questions";
import { useRun } from "../../src/store/run";
test("OpenUI question controls refuse forged, unknown and cross-run references", () => {
  useQuestionStore.setState({ records: { real: [{ request: { run_id: "real", call_id: "call", questions: [{ id: "q", header: "Choice", text: "Choose", options: [{ id: "a", label: "A", description: "First" }, { id: "b", label: "B", description: "Second" }] }] }, interrupt_id: "graph", status: "pending" }] } });
  useRun.setState({ runId: "other" });
  for (const [runId, callId] of [["fake", "call"], ["real", "fake"], ["real", "call"]]) {
    assert.equal(renderToStaticMarkup(createElement(RegisteredQuestionCard, { runId, callId })), "");
  }
  useQuestionStore.setState({ records: {} }); useRun.getState().reset();
});
