import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, readFile, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { randomBytes, createCipheriv, createDecipheriv } from "node:crypto";
import { Vault, trustedFrame, modelSubmission, type Encryption } from "../../electron/vault";
import { childEnvironment } from "../../electron/sidecar";
import { validateWorkspace } from "../../electron/workspace";
import { homedir } from "node:os";

test("vault persists ciphertext, retains keys, replaces keys and fails closed", async () => {
  const key = randomBytes(32), iv = randomBytes(16);
  const encryption: Encryption = {
    isEncryptionAvailable: () => true,
    encryptString(value) { const cipher = createCipheriv("aes-256-cbc", key, iv); return Buffer.concat([cipher.update(value), cipher.final()]); },
    decryptString(value) { const decipher = createDecipheriv("aes-256-cbc", key, iv); return Buffer.concat([decipher.update(value), decipher.final()]).toString(); },
  };
  const path = join(await mkdtemp(join(tmpdir(), "harness-vault-")), "vault.json");
  const canary = randomBytes(24).toString("hex");
  await new Vault(path, encryption).put("mine", canary);
  assert.ok(!(await readFile(path, "utf8")).includes(canary));
  const restored = new Vault(path, encryption);
  assert.equal((await restored.all()).mine, canary);
  await restored.put("mine", "replacement");
  assert.equal((await restored.all()).mine, "replacement");
  await assert.rejects(restored.put("__proto__", "reserved-id-key"), /Invalid model identifier/);
  assert.equal((await restored.all()).constructor, undefined);
  encryption.isEncryptionAvailable = () => false;
  await assert.rejects(restored.put("mine", canary), /Vault unavailable/);
  await assert.rejects(restored.all(), /Vault unavailable/);
  encryption.isEncryptionAvailable = () => true;
  const beforeFailure = await readFile(path, "utf8");
  encryption.encryptString = () => { throw new Error("Encryption failed"); };
  await assert.rejects(restored.put("mine", canary), /Encryption failed/);
  assert.equal(await readFile(path, "utf8"), beforeFailure);
  encryption.decryptString = () => { throw new Error("Decryption failed"); };
  await assert.rejects(restored.all(), /Decryption failed/);
  const blocked = join(await mkdtemp(join(tmpdir(), "harness-vault-failure-")), "not-a-folder");
  await writeFile(blocked, "unchanged");
  await assert.rejects(new Vault(join(blocked, "vault.json"), encryption).put("mine", canary));
  assert.equal(await readFile(blocked, "utf8"), "unchanged");
});

test("IPC frame and model submission validation reject lookalikes and extra properties", () => {
  assert.ok(trustedFrame("app://codeharness/settings/"));
  for (const url of [undefined, "https://codeharness/", "app://codeharness.evil/", "app://user@codeharness/"]) assert.equal(trustedFrame(url), false);
  const valid = { id: "mine", name: "mine", model: "model", base_url: "https://api.example.invalid/v1" };
  assert.ok(modelSubmission.safeParse(valid).success);
  for (const extra of [{ price: 1 }, { api_key: "" }, { base_url: "https://user:secret@x" }, { id: "demo" }]) assert.equal(modelSubmission.safeParse({ ...valid, ...extra }).success, false);
});

test("child environments omit credentials/tracing and native validation refuses home and root", async () => {
  const old = process.env.CODEHARNESS_API_KEY;
  process.env.CODEHARNESS_API_KEY = "synthetic-child-canary";
  try {
    const environment = childEnvironment();
    assert.equal(environment.CODEHARNESS_API_KEY, undefined);
    assert.equal(environment.LANGSMITH_TRACING, "false");
    assert.ok(!JSON.stringify(environment).includes("synthetic-child-canary"));
  } finally { if (old === undefined) delete process.env.CODEHARNESS_API_KEY; else process.env.CODEHARNESS_API_KEY = old; }
  await assert.rejects(validateWorkspace(homedir()));
  await assert.rejects(validateWorkspace(process.cwd().slice(0, 3)));
  const project = await mkdtemp(join(tmpdir(), "harness-valid-folder-"));
  assert.ok(await validateWorkspace(project));
  await symlink(homedir(), join(project, "home-alias"), "junction");
  await assert.rejects(validateWorkspace(join(project, "home-alias")));
  await assert.rejects(validateWorkspace("//localhost/C$/"));
});

test("layout declarations use logical properties for directional spacing", async () => {
  const css = await readFile("src/app/globals.css", "utf8");
  assert.ok(!/(?:margin|padding|inset|border)-(?:left|right|top|bottom)\s*:/i.test(css));
  assert.ok(!/(?:^|[;{])\s*(?:left|right)\s*:/im.test(css));
});
