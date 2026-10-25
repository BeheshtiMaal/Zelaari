export interface TreeFile {
  name: string;
  path: string;
  created: boolean;
}
export interface TreeDir {
  name: string;
  path: string;
  dirs: TreeDir[];
  files: TreeFile[];
}

const byName = (left: string, right: string) => left.localeCompare(right, "en", { sensitivity: "base" });

/**
 * Group changed paths into a folder tree. Paths are workspace-relative and `/`-separated;
 * a segment is never interpreted, so a rendered tree cannot reach outside the list it was given.
 */
export function buildTree(files: { path: string; created?: boolean }[]): TreeDir {
  const root: TreeDir = { name: "", path: "", dirs: [], files: [] };
  for (const file of files) {
    const segments = file.path.split("/").filter(Boolean);
    if (segments.length === 0) continue;
    const name = segments[segments.length - 1];
    let node = root;
    for (const segment of segments.slice(0, -1)) {
      const path = node.path ? `${node.path}/${segment}` : segment;
      let child = node.dirs.find(dir => dir.name === segment);
      if (!child) {
        child = { name: segment, path, dirs: [], files: [] };
        node.dirs.push(child);
      }
      node = child;
    }
    if (node.files.some(existing => existing.name === name)) continue;
    node.files.push({ name, path: file.path, created: file.created ?? false });
  }
  const sort = (dir: TreeDir) => {
    dir.dirs.sort((left, right) => byName(left.name, right.name));
    dir.files.sort((left, right) => byName(left.name, right.name));
    dir.dirs.forEach(sort);
  };
  sort(root);
  return root;
}
