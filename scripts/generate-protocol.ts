import { readFile, mkdir, writeFile } from "node:fs/promises";
import { compile, type JSONSchema } from "json-schema-to-typescript";
const schema = JSON.parse(await readFile("artifacts/protocol.schema.json", "utf8")) as JSONSchema;
const source = await compile(schema, "Protocol", { bannerComment: "/* Generated from backend/agent/events.py. Run npm run generate:protocol. */", additionalProperties: false });
await mkdir("src/lib", { recursive: true });
await writeFile("src/lib/protocol.ts", source + '\nexport type HarnessEvent = Protocol["event"];\n');
