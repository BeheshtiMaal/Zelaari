import { diffLines } from "../../lib/diff";
export function DiffView({ diff }: { diff: string }) {
  return <div className="diff-view" dir="ltr" role="region" aria-label="Unified diff" tabIndex={0} data-testid="diff-view">
    {diffLines(diff).map((line, index) => <div key={index} className={`diff-line ${line.kind}`}>
      <span className="line-number">{line.old ?? ""}</span><span className="line-number">{line.next ?? ""}</span><code>{line.text}</code>
    </div>)}
  </div>;
}
