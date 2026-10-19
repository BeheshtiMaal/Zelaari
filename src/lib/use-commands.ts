"use client";
import { useState, type KeyboardEvent } from "react";
import { commandMatches } from "./commands";
export function useCommands(task: string, setTask: (value: string) => void) {
  const [dismissed, setDismissed] = useState<string | null>(null);
  const matches = dismissed === task ? [] : commandMatches(task);
  function choose(command: string) { setTask(`${command} `); setDismissed(null); }
  function keyDown(event: KeyboardEvent<HTMLTextAreaElement>): boolean {
    if (!matches.length || event.nativeEvent.isComposing) return false;
    if (event.key === "Escape") { event.preventDefault(); setDismissed(task); return true; }
    if (["ArrowDown", "ArrowUp"].includes(event.key)) { event.preventDefault(); return true; }
    if (event.key === "Enter") { event.preventDefault(); choose(matches[0]); return true; }
    return false;
  }
  return { matches, choose, keyDown };
}
