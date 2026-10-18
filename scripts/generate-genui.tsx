import { writeFile } from "node:fs/promises";
import { library } from "../src/genui/library";
await writeFile("backend/agent/genui_prompt.txt", library.prompt() + "\n");
