import assert from "node:assert/strict";
import { test } from "node:test";
import { parseProviderEnv } from "../../electron/provider-config";
test("external provider file parses only its three allowed fields", () => {
  assert.deepEqual(parseProviderEnv('\ufeff# Comment\r\nCODEHARNESS_MODEL="demo-model"\r\nCODEHARNESS_API_KEY=fixture-key\r\nCODEHARNESS_BASE_URL=https://example.invalid/v1\r\nLANGSMITH_TRACING=true\r\nPATH=bad'), {
    CODEHARNESS_MODEL: "demo-model", CODEHARNESS_API_KEY: "fixture-key", CODEHARNESS_BASE_URL: "https://example.invalid/v1",
  });
});
