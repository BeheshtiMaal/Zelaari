import { createLibrary, defineComponent } from "@openuidev/react-lang";
import { z } from "zod/v4";

const Callout = defineComponent({
  name: "Callout", description: "A status message",
  props: z.object({ text: z.string() }),
  component: ({ props }) => <aside data-testid="callout">{props.text}</aside>,
});
const KeyValue = defineComponent({
  name: "KeyValue", description: "A labeled value",
  props: z.object({ label: z.string(), value: z.string() }),
  component: ({ props }) => <dl data-testid="keyvalue"><dt>{props.label}</dt><dd>{props.value}</dd></dl>,
});
const Stack = defineComponent({
  name: "Stack", description: "Vertical content",
  props: z.object({ children: z.array(z.union([Callout.ref, KeyValue.ref])) }),
  component: ({ props, renderNode }) => <section data-testid="stack">{renderNode(props.children)}</section>,
});
export const library = createLibrary({ components: [Callout, KeyValue, Stack], root: "Stack" });
export const program = 'root = Stack([Callout("Hello"), KeyValue("State", "Ready")]);';
