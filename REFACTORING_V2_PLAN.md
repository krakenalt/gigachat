# Repository Refactor V2 Plan

## Summary

- Refactor the SDK around clear layers and names: `clients`, `resources`, `transport`, and `schemas` instead of the current vague `api` / `models` split.
- Use a staged migration: introduce canonical semantic names now, keep old imports and symbols as deprecated aliases for a full migration window.
- Treat current `ChatV2` naming as a symptom of a larger issue: version-specific behavior should live in explicitly named legacy/structured modules, not leak as ad-hoc `V2` suffixes across the whole repo.

## Key Changes

- Replace the current low-level `api` package with a `transport` package that is explicitly HTTP-facing and contains endpoint call builders plus shared HTTP helpers.
- Replace the current `models` package with a `schemas` package that contains Pydantic request/response DTOs only.
- Split the monolithic client implementation into `clients.base`, `clients.sync`, `clients.async`, and `clients.parsing`, with the existing compatibility facade kept in place.
- Move assistant/thread subclients into a `resources` package so they are clearly distinguished from transport modules and Pydantic schemas.
- Rename the current `/chat/completions` schema/transport family to `legacy_chat` and the current `/v2/chat/completions` family to `structured_chat`.
- Rename collection wrappers away from bare plurals. Canonical names become `AssistantList`, `BatchList`, `ModelList`, and `ThreadList`.
- Rename the current `models.models` domain to `model_catalog`, with canonical types `ModelInfo` and `ModelList`.
- Introduce semantic canonical schema names:
  - Legacy endpoint: `LegacyChatRequest`, `LegacyChatResponse`, `LegacyChatStreamChunk`, `LegacyMessage`, `LegacyMessageRole`, `CompletionChoice`.
  - Structured endpoint: `StructuredChatRequest`, `StructuredChatResponse`, `StructuredChatStreamChunk`, `StructuredMessage`, `StructuredContentPart`, `StructuredTool`.
- Keep old names like `Chat`, `ChatV2`, `ChatCompletionV2`, `Messages`, `Models`, and old module paths as deprecated aliases served from a dedicated compatibility layer.
- Keep existing public entry points working, but make semantic names the documented default immediately.
- Normalize async subclient naming so async clients expose `.assistants` and `.threads`; keep `.a_assistants` and `.a_threads` as deprecated aliases.
- Keep the hybrid `GigaChat` class only as a compatibility wrapper; new logic should target the explicit sync/async client classes first.
- Audit docs/examples during the refactor and remove stale references like `DefaultAioHttpClient` unless that symbol is actually implemented and supported.

## Public API / Interface Decisions

- Canonical package layout becomes `gigachat.clients`, `gigachat.resources`, `gigachat.transport`, and `gigachat.schemas`.
- Canonical naming convention becomes `<Domain><Request|Response|StreamChunk>` for DTOs and `<Singular>List` for collection responses.
- Old imports remain valid during migration and emit `DeprecationWarning`; README, examples, and new tests use canonical names only.
- No wire-format or HTTP-behavior changes are part of this refactor; this is strictly a structure, naming, and compatibility cleanup.

## Test Plan

- Add characterization tests before moving code to lock current request payloads, response parsing, headers, retries, streaming SSE parsing, and deprecation behavior.
- Add compatibility tests for old module paths, old type names, old `chat_v2` / `stream_v2` / `chat_parse_v2` entry points, and old async subclient aliases.
- Add import-surface tests for the top-level package and compatibility layer so docs/examples cannot reference unsupported exports again.
- Run the full unit suite, then integration smoke tests for legacy chat, structured chat, embeddings, model catalog, token counting, files, assistants, threads, and batches.
- Smoke-check every documented runnable example script that remains in the repo after cleanup.

## Assumptions

- This is a staged cleanup, not a breaking one-shot rewrite.
- Semantic names are preferred over raw `V2` suffixes.
- The legacy and structured chat APIs must coexist during the migration window.
- `REFACTORING_V2_PLAN.md` should contain this plan verbatim once execution mode is enabled.
