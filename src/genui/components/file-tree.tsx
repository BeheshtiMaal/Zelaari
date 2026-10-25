"use client";
import { genuiCopy, fileCount } from "../../i18n/genui";
import { buildTree, type TreeDir } from "../../lib/genui-tree";
import { currentLocale } from "../../lib/locale";
import { useRunFiles } from "../../lib/use-run-files";
import { useRun } from "../../store/run";
import { GenUiNotFound } from "./not-found";

function Branch({ dir, depth }: { dir: TreeDir; depth: number }) {
  return <ul className="genui-tree" role="group">
    {dir.dirs.map(child => <li key={`d:${child.path}`}>
      <span className="genui-tree-dir" style={{ paddingInlineStart: `${depth * 14}px` }}>{child.name}/</span>
      <Branch dir={child} depth={depth + 1} />
    </li>)}
    {dir.files.map(file => <li key={`f:${file.path}`} className="genui-tree-file" style={{ paddingInlineStart: `${depth * 14}px` }}>
      <code dir="ltr">{file.name}</code>
      {file.created && <span className="genui-tree-new">+</span>}
    </li>)}
  </ul>;
}

/** The paths this run changed, read from the engine's snapshots. */
export function RegisteredFileTree({ runId }: { runId: string }) {
  const active = useRun(state => state.runId);
  const { files, loading, failed } = useRunFiles(runId);
  const locale = currentLocale(), t = genuiCopy(locale);
  if (active !== runId) return <GenUiNotFound what="FileTree" />;
  if (loading && files.length === 0) return <p className="muted" role="status">{t.loadingFiles}</p>;
  if (failed) return <GenUiNotFound what="FileTree" />;
  if (files.length === 0) return <p className="muted" role="status">{t.noChangedFiles}</p>;
  const tree = buildTree(files);
  return <section className="genui-filetree" data-testid="genui-filetree" aria-label={t.changedFiles}>
    <header>
      <strong>{t.changedFiles}</strong>
      <span className="muted">{fileCount(t.files, files.length, locale)}</span>
    </header>
    <Branch dir={tree} depth={0} />
  </section>;
}
