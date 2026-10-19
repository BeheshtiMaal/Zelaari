import { createLibrary, defineComponent } from "@openuidev/react-lang";
import { z } from "zod/v4";
import { DiffView as DiffComponent } from "../components/approvals/diff-view";
import { RegisteredApprovalCard } from "../components/approvals/approval-card";

const ApprovalCard = defineComponent({
  name: "ApprovalCard", description: "Review an existing engine approval by its exact IDs; cannot create permissions",
  props: z.object({ runId: z.string(), approvalId: z.string() }),
  component: ({ props }) => <RegisteredApprovalCard {...props} />,
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
const Stack = defineComponent({
  name: "Stack", description: "Vertical content",
  props: z.object({ children: z.array(z.union([Callout.ref, KeyValue.ref, ApprovalCard.ref, DiffView.ref])) }),
  component: ({ props, renderNode }) => <section className="genui-stack" data-testid="stack">{renderNode(props.children)}</section>,
});
export const library = createLibrary({ components: [Callout, KeyValue, ApprovalCard, DiffView, Stack], root: "Stack" });
