import type { FileContent, FileEntry, FileListing } from "./protocol";

/** Workspace-relative POSIX path for a child of `parent` (`""` is the root). */
export function childPath(parent: string, name: string): string {
  return parent ? `${parent}/${name}` : name;
}

/** The parent of a workspace-relative path; the root is `""`. */
export function parentPath(path: string): string {
  const cut = path.lastIndexOf("/");
  return cut < 0 ? "" : path.slice(0, cut);
}

export function isSystemPath(path: string): boolean {
  return path.split("/")[0].toLowerCase() === ".harness";
}

/** Folders first, then files, both case-insensitive; the engine sorts the same way. */
export function sortEntries(entries: FileEntry[]): FileEntry[] {
  return [...entries].sort((left, right) =>
    left.kind === right.kind ? left.name.localeCompare(right.name, undefined, { sensitivity: "base" }) :
      left.kind === "dir" ? -1 : 1);
}

/**
 * Inclusive 1-based ranges as a set of line numbers, for the viewer's highlight.
 *
 * The generated `ChangedLines` type loses the tuple's element type (the schema
 * generator does not read `prefixItems`), so the shape is narrowed here once.
 */
export function changedLineSet(ranges: unknown): Set<number> {
  const lines = new Set<number>();
  for (const range of (ranges as [number, number][] | undefined) ?? []) {
    for (let line = range[0]; line <= range[1]; line += 1) lines.add(line);
  }
  return lines;
}

export function fileOf(listing: FileListing | null): FileContent | null {
  return listing?.kind === "file" ? listing.file ?? null : null;
}

export function entriesOf(listing: FileListing | null): FileEntry[] {
  return listing?.kind === "dir" ? sortEntries(listing.entries ?? []) : [];
}

/** `path · branch`, the subtitle the mock shows under the folder name. */
export function workspaceSubtitle(path: string, branch: string | null): string {
  return branch ? `${path} · ${branch}` : path;
}
