import * as Tooltip from "@radix-ui/react-tooltip";

export function Hint({ text, children }: {text: string; children: React.ReactNode}) {
  return <Tooltip.Provider><Tooltip.Root><Tooltip.Trigger asChild><span tabIndex={0} className="hint-trigger" aria-label={text}>{children}</span></Tooltip.Trigger><Tooltip.Portal><Tooltip.Content className="tooltip" sideOffset={10}>{text}</Tooltip.Content></Tooltip.Portal></Tooltip.Root></Tooltip.Provider>;
}
