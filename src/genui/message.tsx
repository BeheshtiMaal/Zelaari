"use client";
import { Renderer, type OpenUIError } from "@openuidev/react-lang";
import { Component, useCallback, useRef, useState, type ReactNode } from "react";
import { library } from "./library";

class RenderBoundary extends Component<{ children: ReactNode; text: string }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? <pre className="readable" data-testid="fallback">{this.props.text}</pre> : this.props.children; }
}

export function Message({ text, streaming }: { text: string; streaming: boolean }) {
  const [failed, setFailed] = useState(false);
  const latest = useRef({ text, streaming }); latest.current = { text, streaming };
  const onError = useCallback((errors: OpenUIError[]) => {
    if (latest.current.text.trim() && !latest.current.streaming && errors.some(error => error.severity !== "warning")) setFailed(true);
  }, []);
  if (!text.trimStart().startsWith("root") || failed) return <pre className="readable" data-testid={failed ? "fallback" : "message-text"} dir="auto">{text}</pre>;
  return <RenderBoundary text={text}><Renderer response={text} library={library} isStreaming={streaming} onError={onError} /></RenderBoundary>;
}
