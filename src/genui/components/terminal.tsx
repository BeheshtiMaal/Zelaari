"use client";
import { lazy, Suspense } from "react";
import { currentLocale } from "../../lib/locale";
import type { TestResult } from "../../lib/protocol";
import { useRun } from "../../store/run";
import { GenUiNotFound } from "./not-found";

// Loaded on render, not on import: the library module is also read by the contract generator
// in Node, where xterm has no business being.
const TerminalPanel = lazy(() => import("../../components/terminal/terminal-panel").then(module => ({ default: module.TerminalPanel })));
const TestResults = lazy(() => import("../../components/terminal/test-results").then(module => ({ default: module.TestResults })));

type Call = { command: string; result: string | null; test: TestResult | null };

/** A command and its output, read from the run's own events — never from the program. */
function useCall(runId: string, callId: string): Call | null {
  const active = useRun(state => state.runId);
  const events = useRun(state => state.events);
  if (active !== runId) return null;
  const call = events.find(event => event.type === "tool.call" && event.call_id === callId);
  const command = call?.type === "tool.call" && typeof call.args.command === "string" ? call.args.command : null;
  if (command === null) return null;
  const result = events.find(event => event.type === "tool.result" && event.call_id === callId);
  const test = events.find(event => event.type === "test.result" && event.call_id === callId);
  return {
    command,
    result: result?.type === "tool.result" ? result.text : null,
    test: test?.type === "test.result" ? test : null,
  };
}

export function RegisteredTerminalPanel({ runId, callId }: { runId: string; callId: string }) {
  const call = useCall(runId, callId);
  if (!call) return <GenUiNotFound what="TerminalPanel" />;
  return <Suspense fallback={null}><TerminalPanel command={call.command} result={call.result} locale={currentLocale()} /></Suspense>;
}

export function RegisteredTestResults({ runId, callId }: { runId: string; callId: string }) {
  const call = useCall(runId, callId);
  if (!call?.test) return <GenUiNotFound what="TestResults" />;
  return <Suspense fallback={null}><TestResults result={call.test} locale={currentLocale()} /></Suspense>;
}
