# Phase 2 contracts and verified APIs

All routes use existing bearer auth and locked origins.

| Method/path | Input | Public output |
|---|---|---|
| GET /models | none | ProviderRecord[] including demo |
| POST /models | ModelInput | ProviderRecord; retained key only |
| POST /models/{id}/test | none | ProviderRecord; GET /models exposes retry state |
| GET /presets | none | Preset[] |
| GET /settings | none | Settings |
| PUT /settings | Settings | Settings; rejects unusable defaults |
| POST /internal/credentials | id + SecretStr key | status only; memory-only, no read route |
| GET /workspaces | none | WorkspaceState including task index |
| POST /workspaces | path | WorkspaceState; canonical validation |
| GET /tasks/{id}/events | none | SSE replay from jailed app-indexed event log |

Preload adds saveModel(ModelInput & {api_key?: string}), vaultStatus() and native
pickWorkspace(). Main serializes saves, validates trusted frame/payload, encrypts
keys before writing disk, synchronizes engine memory, then saves metadata.
Interrupted saves leave encrypted recoverable keys, never plaintext. Engine persists
only nonsecret metadata/settings/task index atomically under app data. Main owns a
separate encrypted vault there. Bootstrap pipe carries app-data path, no key env.
Restore failures are visible and leave affected providers unusable.

Verified local versions: Electron 44.9.0; deepagents 0.7.28; langchain-openai 1.7.2;
langchain-anthropic 1.7.6; FastAPI 0.146.0; httpx 0.28.1. Electron d.ts exposes
isEncryptionAvailable(), encryptString(string): Buffer, decryptString(Buffer): string.
OpenAI adapter source drops reasoning_content, requiring narrow conversion overrides;
Anthropic source preserves thinking. Bridge must handle structured blocks.
Context table gpt-4.1 source: https://developers.openai.com/api/docs/models/gpt-4.1.
Models metadata reads positive context_window/context_length on matching entries,
when supplied; absence falls through rather than inventing metadata.
