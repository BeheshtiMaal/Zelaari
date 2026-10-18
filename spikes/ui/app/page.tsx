"use client";
import { Renderer, type OpenUIError } from "@openuidev/react-lang";
import { useCallback, useEffect, useRef, useState } from "react";
import { library, program } from "./library";

export default function Page() {
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => setHydrated(true), []);
  const [response, setResponse] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [failed, setFailed] = useState(false);
  const [diagnostics, setDiagnostics] = useState("");
  const latest = useRef({ response, streaming });
  latest.current = { response, streaming };
  const onError = useCallback((errors: OpenUIError[]) => {
    setDiagnostics(JSON.stringify(errors));
    if (latest.current.response.trim() && !latest.current.streaming && errors.some(error => error.severity !== "warning")) setFailed(true);
  }, []);
  return <main data-hydrated={hydrated}>
    <h1>OpenUI technical spike</h1>
    <button onClick={() => { setFailed(false); setStreaming(true); setResponse('root = Stack([Callout("Hel'); }}>Start</button>
    <button onClick={() => setResponse('root = Stack([Callout("Hello"), KeyValue("State", "Re')}>Chunk</button>
    <button onClick={() => { setFailed(false); setResponse(program); setStreaming(false); }}>Finish</button>
    <button onClick={() => { setFailed(false); setStreaming(false); setResponse('root = Missing("bad input");'); }}>Malformed</button>
    {failed ? <pre data-testid="fallback">{response}</pre> : <Renderer response={response} library={library} isStreaming={streaming} onError={onError} />}
    <pre data-testid="diagnostics" hidden>{diagnostics}</pre>
    <details><summary>Generated prompt</summary><pre data-testid="prompt">{library.prompt()}</pre></details>
  </main>;
}
