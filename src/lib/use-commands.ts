"use client";
import { useEffect, useState, type KeyboardEvent } from "react";
import { api } from "./api";
import type { SkillCommand } from "./protocol";
import { activeCommand, commandMatches } from "./commands";

/** The workspace's commands, refreshed when the workspace changes. */
export function useCommandList(workspace: string): SkillCommand[] {
  const [list, setList] = useState<SkillCommand[]>([]);
  useEffect(() => {
    if (!workspace) { setList([]); return; }
    let live = true;
    api<SkillCommand[]>(`/skills/commands?workspace=${encodeURIComponent(workspace)}`)
      .then(items => { if (live) setList(items); })
      .catch(() => { if (live) setList([]); });
    return () => { live = false; };
  }, [workspace]);
  return list;
}

export function useCommands(task: string, setTask: (value: string) => void, list: SkillCommand[] = []) {
  const [dismissed, setDismissed] = useState<string | null>(null);
  const [index, setIndex] = useState(0);
  const matches = dismissed === task ? [] : commandMatches(task, list);
  const active = activeCommand(task, list);
  useEffect(() => { setIndex(0); }, [task]);

  function choose(command: string) {
    setTask(`${command} `);
    setDismissed(null);
    setIndex(0);
  }

  function keyDown(event: KeyboardEvent<HTMLTextAreaElement>): boolean {
    if (!matches.length || event.nativeEvent.isComposing) return false;
    if (event.key === "Escape") { event.preventDefault(); setDismissed(task); return true; }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setIndex(current => (current + 1) % matches.length);
      return true;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      setIndex(current => (current - 1 + matches.length) % matches.length);
      return true;
    }
    if (event.key === "Enter") {
      event.preventDefault();
      choose((matches[Math.min(index, matches.length - 1)] ?? matches[0]).command);
      return true;
    }
    return false;
  }

  return { matches, index, active, choose, keyDown };
}
