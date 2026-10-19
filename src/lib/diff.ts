export interface DiffLine { kind: "context" | "add" | "remove" | "header"; old: number | null; next: number | null; text: string }
export function diffLines(source: string): DiffLine[] {
  let old = 0, next = 0, inHunk = false;
  return source.split("\n").filter((line, index, all) => line || index < all.length - 1).map(text => {
    const hunk = /^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/.exec(text);
    if (hunk) { old = Number(hunk[1]); next = Number(hunk[2]); inHunk = true; }
    if (hunk || (!inHunk && (text.startsWith("---") || text.startsWith("+++"))) || text.startsWith("\\")) return { kind: "header", old: null, next: null, text };
    if (text.startsWith("+")) return { kind: "add", old: null, next: next++, text };
    if (text.startsWith("-")) return { kind: "remove", old: old++, next: null, text };
    return { kind: "context", old: old++, next: next++, text };
  });
}
