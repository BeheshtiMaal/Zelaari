import { createLibrary, defineComponent } from "@openuidev/react-lang";
import { z } from "zod/v4";
import { DiffView as DiffComponent } from "../components/approvals/diff-view";
import { RegisteredApprovalCard } from "../components/approvals/approval-card";
import { RegisteredQuestionCard } from "../components/questions/question-card";
import { RegisteredPlanChecklist } from "../components/planning/plan-checklist";
import { RegisteredFileTree } from "./components/file-tree";
import { RegisteredTerminalPanel, RegisteredTestResults } from "./components/terminal";
import { TableView } from "./components/table";
import { TabsView } from "./components/tabs";

/**
 * The library is the only definition of what the model may render: the prompt and the JSON
 * schema are both generated from it, and the engine validates against that schema.
 *
 * Engine-state components take ids only, so no component can be told to approve, answer,
 * execute or invent state. Presentational components take strings, numbers and booleans.
 */

const PlanChecklist = defineComponent({
  name: "PlanChecklist", description: "Display the active engine plan using its exact run, plan and revision IDs; it takes ids only and cannot set progress or approve",
  props: z.object({ runId: z.string(), planId: z.string(), revision: z.string() }),
  component: ({ props }) => <RegisteredPlanChecklist {...props} />,
});

const QuestionCard = defineComponent({
  name: "QuestionCard", description: "Answer an existing engine question using its exact run and call IDs; it takes ids only and cannot create a question",
  props: z.object({ runId: z.string(), callId: z.string() }),
  component: ({ props }) => <RegisteredQuestionCard {...props} />,
});

const ApprovalCard = defineComponent({
  name: "ApprovalCard", description: "Review an existing engine approval by its exact run and approval IDs; it takes ids only and cannot create permissions",
  props: z.object({ runId: z.string(), approvalId: z.string() }),
  component: ({ props }) => <RegisteredApprovalCard {...props} />,
});

const TerminalPanel = defineComponent({
  name: "TerminalPanel", description: "Read-only output of a command this run already ran, by its exact run and call IDs; it takes ids only and never executes anything",
  props: z.object({ runId: z.string(), callId: z.string() }),
  component: ({ props }) => <RegisteredTerminalPanel {...props} />,
});

const TestResults = defineComponent({
  name: "TestResults", description: "Counts and failures of a test command this run already ran, by its exact run and call IDs; it takes ids only and never runs tests",
  props: z.object({ runId: z.string(), callId: z.string() }),
  component: ({ props }) => <RegisteredTestResults {...props} />,
});

const FileTree = defineComponent({
  name: "FileTree", description: "The files this run actually changed, read from the engine by run ID; it takes ids only and never a path list",
  props: z.object({ runId: z.string() }),
  component: ({ props }) => <RegisteredFileTree {...props} />,
});

const DiffView = defineComponent({
  name: "DiffView", description: "Unified diff with old/new line numbers",
  props: z.object({ diff: z.string() }),
  component: ({ props }) => <DiffComponent diff={props.diff} />,
});

const Callout = defineComponent({
  name: "Callout", description: "A short status or summary",
  props: z.object({ text: z.string() }),
  component: ({ props }) => <aside className="genui-callout" data-testid="callout">{props.text}</aside>,
});

const KeyValue = defineComponent({
  name: "KeyValue", description: "A labeled value",
  props: z.object({ label: z.string(), value: z.string() }),
  component: ({ props }) => <dl className="genui-value" data-testid="keyvalue"><dt>{props.label}</dt><dd dir="auto">{props.value}</dd></dl>,
});

const Table = defineComponent({
  name: "Table", description: "A display-only table: column headers and rows of cells, all strings",
  props: z.object({ columns: z.array(z.string()), rows: z.array(z.array(z.string())) }),
  component: ({ props }) => <TableView columns={props.columns} rows={props.rows} />,
});

/** Everything that can sit inside a `Stack`, in the order the prompt lists it. */
const leaves = [Callout, KeyValue, Table, DiffView, FileTree, TerminalPanel, TestResults, ApprovalCard, QuestionCard, PlanChecklist];

/**
 * The sub-component position of every container accepts the whole library, including the
 * container itself: a reference and an inline call must mean the same thing. Recursion is
 * bounded by the validator's depth limit, not by the schema.
 */
function everyComponent() {
  return [...leaves, Stack, Tabs].map(component => component.ref);
}

const Stack = defineComponent({
  name: "Stack", description: "Vertical content; children are references to other statements",
  props: z.object({ children: z.array(z.lazy((): z.ZodType => z.union(everyComponent()))) }),
  component: ({ props, renderNode }) => <section className="genui-stack" data-testid="stack">{renderNode(props.children)}</section>,
});

const Tabs = defineComponent({
  name: "Tabs", description: "Tabbed panels: labels and panels are two positional arrays of equal length; a panel is a reference to one statement",
  props: z.object({ labels: z.array(z.string()), panels: z.array(z.lazy((): z.ZodType => z.union(everyComponent()))) }),
  component: ({ props, renderNode }) => {
    const panels = renderNode(props.panels);
    return <TabsView labels={props.labels} panels={Array.isArray(panels) ? panels : []} />;
  },
});

export const library = createLibrary({ components: [...leaves, Stack, Tabs], root: "Stack" });
