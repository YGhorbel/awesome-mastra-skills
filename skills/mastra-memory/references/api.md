# Memory API reference

Distilled from `https://mastra.ai/reference/memory/memory-class.md` and the other `reference/memory/*` pages. Verify against the installed version before relying on an option.

## Contents

- Constructor: `new Memory({...})`
- `options` (MemoryConfig)
- Per-call memory options on `generate()` / `stream()`
- Thread methods
- Message methods
- Working memory methods
- Clone methods and utilities
- Summaries and background work
- `MastraDBMessage`
- Built-in memory processors

---

## Constructor: `new Memory({...})`

Import: `import { Memory } from '@mastra/memory'`

| Option | Type | Notes |
|---|---|---|
| `storage` | `MastraCompositeStore` | Optional. Falls back to the Mastra instance storage. With neither, accessing storage throws "Memory requires a storage provider to function". |
| `vector` | `MastraVector \| false` | Vector store for semantic recall. `false` disables vector operations. See `mastra-semantic-recall`. |
| `embedder` | `string \| EmbeddingModel \| EmbeddingModelV2` | Router ID such as `'openai/text-embedding-3-small'`. Required for semantic recall unless the vector store embeds itself. |
| `embeddingDimension` | `number` | Skips the probe embedding on first use. Must match the embedder output. |
| `options` | `MemoryConfig` | See below. |

---

## `options` (MemoryConfig)

| Option | Type | Default | Notes |
|---|---|---|---|
| `lastMessages` | `number \| false` | `10` | Recent messages loaded into context. `false` disables history (nothing loaded or saved). Counts tool calls, tool results, and signals. |
| `messageHistory` | `{ maxTokens: number; atMaxRemoveTokens?: number }` | none | Token budget for the whole prompt. Drops oldest remembered messages down to `maxTokens - atMaxRemoveTokens` (default 25% of `maxTokens`). Without `lastMessages`, removes the 10-message cap. `maxTokens: 0` disables history. |
| `readOnly` | `boolean` | `false` | Load but do not save. Working memory shown without the update tool. |
| `retainFullInput` | `boolean` | `false` | Process input exactly as sent instead of filtering client-echoed history. Unstored input messages are saved. |
| `semanticRecall` | `boolean \| { topK, messageRange, scope?, filter?, indexConfig? }` | `false` | See `mastra-semantic-recall`. |
| `workingMemory` | `{ enabled, template?, schema?, scope?, readOnly?, useStateSignals? }` | disabled | `scope: 'resource'` default. `template` or `schema`, not both. |
| `observationalMemory` | `boolean \| ObservationalMemoryOptions` | `false` | See `mastra-observational-memory`. |
| `generateTitle` | `boolean \| { model?, instructions?, minMessages?, emitEvent? }` | `false` | Model defaults to the agent's model. `emitEvent: true` makes `stream()` emit a transient `data-thread-title` chunk before `finish`. |

### workingMemory fields

| Field | Notes |
|---|---|
| `enabled` | `true` to turn on. |
| `scope` | `'resource'` (default, shared across a resource's threads) or `'thread'`. Scopes are fully separate. |
| `template` | Markdown block. Replace semantics: the agent sends the full block on each update. |
| `schema` | zod or JSON Schema object. Merge semantics: objects deep merge, `null` deletes a field, arrays replace. |
| `useStateSignals` | Experimental. Delivers working memory as a state signal; tool is renamed `setWorkingMemory`. Not supported with template `version: 'vnext'`. |

Resource scope requires an adapter with the `mastra_resources` table: `@mastra/libsql`, `@mastra/pg`, `@mastra/oracledb`, `@mastra/upstash`, `@mastra/mongodb`.

---

## Per-call memory options on `generate()` / `stream()`

```typescript
await agent.generate('Hello', {
  memory: {
    thread: { id: 'thread-123', title: 'Support conversation', metadata: { category: 'billing' } },
    resource: 'user-456',
    options: { readOnly: true }, // any MemoryConfig field, merged for this call
  },
})
```

| Field | Type | Notes |
|---|---|---|
| `resource` | `string` | Owner of the thread. Fixed once the thread exists. |
| `thread` | `string \| { id, title?, metadata? }` | Conversation ID. Created on first use. |
| `options` | `MemoryConfig` | Per-call overrides. |

Alternative: `scopes: ['resource:<id>', 'thread:<id>', 'org:acme']`. Memory reads `resource:` and `thread:` scopes. Conflicting values across `memory`, scopes, and request context throw.

Get the instance: `const memory = await agent.getMemory()`.

---

## Thread methods

| Method | Signature | Returns |
|---|---|---|
| `createThread` | `({ resourceId, threadId?, title?, metadata? })` | Thread `{ id, resourceId, title, createdAt, updatedAt, metadata }` |
| `getThreadById` | `({ threadId })` | `StorageThreadType \| null` |
| `listThreads` | `({ filter?: { resourceId?, metadata? }, page?, perPage?, orderBy? })` | `{ threads, total, page, perPage, hasMore }` |
| `updateThread` | `({ id, title, metadata })` | Updated thread. Setting `metadata.workingMemory` sets thread working memory. |
| `updateThreadResourceId` | `({ threadId, resourceId })` | Thread moved to a new owner with all messages. No-op if already owned. Throws if missing. Trusted callers only. |

`listThreads` defaults: `perPage: 100`, `orderBy: { field: 'createdAt', direction: 'DESC' }`. `perPage: false` fetches all. Metadata filters use AND.

---

## Message methods

### `recall(params)`

| Param | Type | Notes |
|---|---|---|
| `threadId` | `string` | Required. |
| `resourceId` | `string` | Validates ownership when set. |
| `perPage` | `number \| false` | Defaults to `threadConfig.lastMessages`. |
| `page` | `number` | Zero-based. |
| `vectorSearchString` | `string` | Semantic search. Needs `threadConfig: { semanticRecall: true }`. |
| `include` | `{ id, threadId?, withPreviousMessages?, withNextMessages? }[]` | Fetch specific messages with context. |
| `filter` | `{ dateRange?: { start?, end?, startExclusive?, endExclusive? }, metadata? }` | Metadata: shallow scalars only, AND semantics, `null` matches explicit null only. |
| `orderBy` | `{ field: 'createdAt', direction }` | Defaults to descending. |
| `hideSignals` | `boolean \| string[]` | Hides reminder signals by default. `false` includes all. Filtering happens after pagination. |
| `threadConfig` | `MemoryConfig` | Retrieval configuration. |

Returns `{ messages: MastraDBMessage[] }`. Convert for AI SDK UIs with `toAISdkV5Messages` from `@mastra/ai-sdk/ui`.

### `saveMessages({ messages, memoryConfig?, observabilityContext? })`

Write messages yourself (seed, import). Each message needs `threadId` and `resourceId`; create the thread first. Returns `{ messages, usage? }`.

### `deleteMessages(ids)`

`ids: string[] | { id: string }[]`. Returns `Promise<void>`. Vector cleanup runs in the background.

---

## Working memory methods

| Method | Notes |
|---|---|
| `updateWorkingMemory({ threadId, resourceId?, workingMemory })` | Replace. `resourceId` required for resource scope. |
| `mergeWorkingMemory({ threadId, resourceId, workingMemory })` | Partial merge. Throws unless schema-based, resource-scoped, and the adapter supports atomic merges (currently `@mastra/pg`). |
| `supportsAtomicWorkingMemoryMerge()` | Check before `mergeWorkingMemory`. |

---

## Clone methods and utilities

| Method | Notes |
|---|---|
| `cloneThread({ sourceThreadId, newThreadId?, resourceId?, title?, metadata?, options? })` | Returns `{ thread, clonedMessages, messageIdMap }`. `options`: `messageLimit`, `messageFilter: { startDate?, endDate?, messageIds? }`. Copies working memory, OM records, and embeddings. |
| `copyThread(sameParams)` | Returns `{ thread, messageIdMap }` without message payloads. In-database copy on libSQL and PostgreSQL. |
| `isClone(thread)` | Boolean. |
| `getCloneMetadata(thread)` | `{ sourceThreadId, clonedAt, lastMessageId? }` or undefined. |
| `getSourceThread(threadId)` | Source thread or null. |
| `listClones(sourceThreadId)` | Threads cloned from it. |
| `getCloneHistory(threadId)` | Chain from original to this thread. |

Clone titles default to `Clone of <title>`. Source metadata is not copied.

---

## Summaries and background work

| API | Notes |
|---|---|
| `memory.summarizeThread({ model, threadId, resourceId?, lastMessages?, maxInputTokens?, instructions?, extract?, requestContext?, abortSignal? })` | One-shot summary of a stored thread. Writes nothing to memory. Returns `{ summary, extracted, extractionFailures?, usage }`. `maxInputTokens` default `1000000`. |
| `summarizeConversation({ model, messages, ... })` | Standalone function from `@mastra/memory` for messages you already hold. |
| `memory.settled(scope?)` | Resolves when background work (OM cycles, vector cleanup) finishes. Await before closing storage you own. |

---

## `MastraDBMessage`

| Field | Notes |
|---|---|
| `id` | Message ID. |
| `role` | `'user' \| 'assistant' \| 'system' \| 'signal'`. System messages and transient signals are not persisted. |
| `threadId`, `resourceId` | Required when saving. |
| `createdAt` | `Date`. |
| `content` | `{ format: 2, parts: [...], metadata? }`. Write to `parts`; `toolInvocations`, `reasoning`, `experimental_attachments` are v4 mirrors. |

Import the type from `@mastra/core/memory`.

---

## Built-in memory processors

Added automatically when memory is enabled. Input order: `MemoryInputFilter`, `WorkingMemory`, `MessageHistory`, `SemanticRecall`, then your `inputProcessors`. Output order: your `outputProcessors`, then `SemanticRecall` (embeddings) and `MessageHistory` (persistence).

- An output guardrail that calls `abort()` prevents saving. An input guardrail abort skips the LLM and saving.
- A caller `abortSignal` still saves the user message and the partial assistant text.
- Adding `MessageHistory` (from `@mastra/core/processors`) to `inputProcessors` yourself stops Mastra adding its own copy.
