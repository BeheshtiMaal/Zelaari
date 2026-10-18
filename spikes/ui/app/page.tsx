"use client";
import { Renderer } from "@openuidev/react-lang";
import { useCallback, useState } from "react";
import { library, program } from "./library";

export default function Page() {
  const [response, setResponse] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [failed, setFailed] = useState(false);
  const onError = useCallback(() => setFailed(true), []);
  return <main>
    <h1>OpenUI technical spike</h1>
    <button onClick={() => { setFailed(false); setStreaming(true); setResponse('root = Stack([Callout("Hel'); }}>Start</button>
    <button onClick={() => setResponse('root = Stack([Callout("Hello"), KeyValue("State", "Re')}>Chunk</button>
    <button onClick={() => { setResponse(program); setStreaming(false); }}>Finish</button>
    <button onClick={() => { setFailed(false); setStreaming(false); setResponse('root = Missing("bad input");'); }}>Malformed</button>
    {failed ? <pre data-testid="fallback">{response}</pre> : <Renderer response={response} library={library} isStreaming={streaming} onError={onError} />}
    <details><summary>Generated prompt</summary><pre data-testid="prompt">{library.prompt()}</pre></details>
  </main>;
}
