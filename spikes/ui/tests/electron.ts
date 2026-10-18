import { _electron as electron, expect } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

await mkdir("../artifacts", { recursive: true });
const results: object[] = [];
for (const protocol of ["file", "app"]) {
  const instance = await electron.launch({ args: [resolve("electron/main.cjs")], env: { ...process.env, SPIKE_PROTOCOL: protocol } });
  const errors: string[] = [];
  try {
    const page = await instance.firstWindow();
    page.on("pageerror", error => errors.push(error.message));
    await expect(page.getByRole("heading")).toHaveText("OpenUI technical spike");
    await page.getByRole("button", { name: "Start", exact: true }).click();
    await expect(page.getByTestId("callout")).toContainText("Hel");
    await page.getByRole("button", { name: "Chunk", exact: true }).click();
    await expect(page.getByTestId("callout")).toHaveText("Hello");
    await page.getByRole("button", { name: "Finish", exact: true }).click();
    await expect(page.getByTestId("keyvalue")).toContainText("Ready");
    await expect(page.getByTestId("stack")).toBeVisible();
    for (const component of ["Callout", "Stack", "KeyValue"]) await expect(page.getByTestId("prompt")).toContainText(component);
    await page.screenshot({ path: `../artifacts/openui-${protocol}.png` });
    await page.getByRole("button", { name: "Malformed", exact: true }).click();
    await expect(page.getByTestId("fallback")).toContainText("bad input");
    expect(errors).toEqual([]);
    results.push({ protocol, passed: true, errors });
  } finally { await instance.close(); }
}
await writeFile("../artifacts/openui.json", JSON.stringify(results, null, 2));
console.log("OpenUI: both protocols, progressive rendering, prompt and fallback passed");
