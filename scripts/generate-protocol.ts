import { readFile, mkdir, writeFile } from "node:fs/promises";
import { compile, type JSONSchema } from "json-schema-to-typescript";
const schema = JSON.parse(await readFile("artifacts/protocol.schema.json", "utf8")) as JSONSchema;
const source = await compile(schema, "Protocol", { bannerComment: "/* Generated from backend/agent/events.py. Run npm run generate:protocol. */", additionalProperties: false });
await mkdir("src/lib", { recursive: true });
await writeFile("src/lib/protocol.ts", source + '\n// Serialized events always include the Pydantic discriminator and timestamp defaults.\ntype WireEvent<E> = E extends { type?: infer K } ? E & { type: K } : never;\nexport type HarnessEvent = WireEvent<Protocol["event"]>;\n');
