import { writeFile } from "node:fs/promises";
import { library } from "../src/genui/library";

/**
 * Two artefacts from one library: the prompt the model reads and the JSON schema the engine
 * validates against. Both are committed, and running this twice must leave both unchanged.
 */
const schema = library.toJSONSchema();
await writeFile("backend/agent/genui_prompt.txt", library.prompt() + "\n");
await writeFile("backend/agent/genui_schema.json", JSON.stringify(schema, null, 2) + "\n");
