import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { library } from "../../src/genui/library";
import { buildTree } from "../../src/lib/genui-tree";

const schema = JSON.parse(readFileSync("backend/agent/genui_schema.json", "utf8"));
const prompt = readFileSync("backend/agent/genui_prompt.txt", "utf8");
const components = Object.keys(schema.properties) as string[];
const defs = schema.$defs as Record<string, { properties: Record<string, { type?: string; items?: { anyOf?: { $ref: string }[] } }> }>;

const ENGINE_STATE = ["TerminalPanel", "TestResults", "FileTree", "ApprovalCard", "QuestionCard", "PlanChecklist"];
const DISPLAY_ONLY = ["Callout", "KeyValue", "Table", "DiffView", "Stack", "Tabs"];
const refs = (anyOf: { $ref: string }[] = []) => anyOf.map(entry => entry.$ref.replace("#/$defs/", ""));

test("the contract names all twelve components", () => {
  assert.deepEqual(components, ["Callout", "KeyValue", "Table", "DiffView", "FileTree", "TerminalPanel", "TestResults", "ApprovalCard", "QuestionCard", "PlanChecklist", "Stack", "Tabs"]);
  assert.deepEqual(Object.keys(defs).sort(), [...components].sort());
});

test("engine-state components take ids only, so nothing can be told to approve or execute", () => {
  for (const name of ENGINE_STATE) {
    const props = Object.entries(defs[name].properties);
    assert.ok(props.length > 0, `${name} declares no props`);
    for (const [prop, spec] of props) {
      assert.match(prop, /^(runId|callId|approvalId|planId|revision)$/, `${name}.${prop} is not an id prop`);
      assert.equal(spec.type, "string", `${name}.${prop} is not a string`);
    }
  }
});

test("display-only components cannot receive an engine id", () => {
  for (const name of DISPLAY_ONLY) {
    for (const prop of Object.keys(defs[name].properties)) {
      assert.doesNotMatch(prop, /Id$/, `${name}.${prop} looks like engine state`);
    }
  }
});

test("Stack and Tabs accept the whole library, including themselves", () => {
  assert.deepEqual(refs(defs.Stack.properties.children.items?.anyOf).sort(), [...components].sort());
  assert.deepEqual(refs(defs.Tabs.properties.panels.items?.anyOf).sort(), [...components].sort());
  assert.equal(defs.Tabs.properties.labels.type, "array");
});

test("the committed artefacts are exactly what the library generates", () => {
  assert.equal(readFileSync("backend/agent/genui_schema.json", "utf8"), JSON.stringify(library.toJSONSchema(), null, 2) + "\n");
  assert.equal(prompt, library.prompt() + "\n");
  for (const name of components) assert.ok(prompt.includes(`${name}(`), `the prompt does not name ${name}`);
  assert.ok(prompt.length < 8_000, "the library prompt must stay inside the preamble budget");
});

test("the changed-file tree nests, sorts and never duplicates a path", () => {
  const tree = buildTree([
    { path: "src/lib/use-run-files.ts", created: true },
    { path: "src/app/page.tsx" },
    { path: "README.md" },
    { path: "src/lib/use-run-files.ts", created: true },
  ]);
  assert.deepEqual(tree.files.map(file => file.name), ["README.md"]);
  assert.deepEqual(tree.dirs.map(dir => dir.name), ["src"]);
  const lib = tree.dirs[0].dirs.find(dir => dir.name === "lib");
  assert.deepEqual(lib?.files, [{ name: "use-run-files.ts", path: "src/lib/use-run-files.ts", created: true }]);
  assert.equal(tree.dirs[0].path, "src");
  assert.deepEqual(buildTree([]).dirs, []);
});
