# @mastra/ai-sdk API reference

Distilled from the pages under `https://mastra.ai/reference/ai-sdk/`. Verify against the installed version.

## Contents

- Shared `version` option
- Route helpers (Mastra server)
- Framework-agnostic handlers
- Stream conversion
- Message converters
- Utilities

---

## Shared `version` option

Every route, handler, `toAISdkStream()`, and `toAISdkMessages()` accepts `version: 'v5' | 'v6' | 'v7'`. Default `'v5'`. Pass the version that matches the installed `ai` package.

---

## Route helpers (Mastra server)

Import from `@mastra/ai-sdk`. Add the result to `server.apiRoutes`.

### `chatRoute(options)`

| Option | Default | Notes |
|---|---|---|
| `path` | `'/chat/:agentId'` | Include `:agentId` for dynamic routing. |
| `agent` | | Fixed agent ID. Required when `path` has no `:agentId`. |
| `agentVersion` | | `{ versionId }` or `{ status: 'draft' \| 'published' }`. Query `?versionId=` or `?status=` wins. Needs the Editor. |
| `defaultOptions` | | `AgentExecutionOptions` (instructions, memory, maxSteps). |
| `sendStart`, `sendFinish` | `true` | Start and finish events. |
| `sendReasoning`, `sendSources` | `false` | Reasoning and source parts. |
| `includeSubAgentMetadata` | `true` | Emit `data-tool-agent` parts for subagents. |
| `messageMetadata` | | `({ part, traceId }) => metadata` on start and finish chunks. |
| `heartbeatMs` | | SSE heartbeat interval. |

Forwards the request `AbortSignal` to `agent.stream()`. Without memory, send the full `messages` array. With memory, send the last message and `memory: { thread, resource }`.

### `workflowRoute(options)`

| Option | Default | Notes |
|---|---|---|
| `path` | `'/api/workflows/:workflowId/stream'` | Include `:workflowId` for dynamic routing. Use a path outside the API prefix such as `/workflow`. |
| `workflow` | | Fixed workflow ID. |
| `includeTextStreamParts` | `true` | Forward agent text piped into the workflow writer. |

### `networkRoute(options)` (deprecated)

`path` (default `'/network/:agentId'`), `agent`, `agentVersion`, `defaultOptions`. Migrate to supervisor agents.

---

## Framework-agnostic handlers

Each returns a `ReadableStream`. Wrap it with `createUIMessageStreamResponse({ stream })` from `ai`.

### `handleChatStream(options)`

| Option | Notes |
|---|---|
| `mastra`, `agentId` | Required. |
| `agentVersion` | As above. |
| `params.messages` | `UIMessage[]`. |
| `params.runId`, `params.resumeData` | Resume a suspended run. `runId` required with `resumeData`. |
| `params.requestContext` | `RequestContext` instance. |
| `params.providerOptions` | Merged over `defaultOptions.providerOptions`. |
| `params.memory` | `{ thread, resource }`. |
| `defaultOptions` | Merged under `params`. |
| `sendStart`, `sendFinish`, `sendReasoning`, `sendSources`, `includeSubAgentMetadata`, `messageMetadata` | Same as `chatRoute()`. |
| `onError` | `(error) => string` sanitized message for the client. |

With `structuredOutput`, the final object arrives as a `data-structured-output` part.

### `handleWorkflowStream(options)`

`mastra`, `workflowId`, `params: { runId?, resourceId?, inputData?, resumeData?, requestContext?, tracingOptions?, step? }`, `includeTextStreamParts` (default `true`).

### `handleNetworkStream(options)` (deprecated)

`mastra`, `agentId`, `agentVersion`, `params` (messages plus execution options), `defaultOptions`.

---

## Stream conversion: `toAISdkStream(stream, options)`

Import: `import { toAISdkStream } from '@mastra/ai-sdk'`

Input: `MastraModelOutput` (`agent.stream()`), `MastraAgentNetworkStream` (`agent.network()`), or a workflow stream (`run.stream()`).

| Option | Default | Scope |
|---|---|---|
| `from` | `'agent'` | `'agent' \| 'network' \| 'workflow'` |
| `lastMessageId` | | Agent |
| `sendStart`, `sendFinish` | `true` | Agent |
| `sendReasoning`, `sendSources` | `false` | Agent |
| `includeSubAgentMetadata` | `false` | Agent (handlers default it to `true`) |
| `includeTextStreamParts` | `true` | Workflow |
| `messageMetadata`, `onError` | | Agent |

Use inside `createUIMessageStream({ originalMessages, execute: async ({ writer }) => { for await (const part of toAISdkStream(...)) await writer.write(part) } })`.

---

## Message converters

Import from `@mastra/ai-sdk/ui`.

| Function | Returns |
|---|---|
| `toAISdkMessages(messages, { version? })` | `UIMessage[]` with `id`, `role`, `parts`, `metadata`. Keeps stored `error` parts for failed turns. |
| `toAISdkV5Messages(messages)` | AI SDK v5 `UIMessage[]`. |
| `toAISdkV4Messages(messages)` | v4 messages with `content`, `parts`, `toolInvocations`, `createdAt`. |

`messages` accepts a string, string array, a message object, or an array in any supported format (for example `memory.recall()` output).

---

## Utilities

| Export | Use |
|---|---|
| `withSseHeartbeat(response, heartbeatMs)` | Wraps an SSE `Response` and sends comments while idle. `0` or less disables. |
| `workflowSnapshotToStream(workflowRun)` | Turns a stored workflow run state into a UI stream for reloads. |
| `withMastra(model, { inputProcessors?, outputProcessors?, memory? })` | Wraps an AI SDK v5 or v6 model with Mastra processors and memory. `memory: { storage, threadId, resourceId, lastMessages?, semanticRecall?, workingMemory?, readOnly? }` where `storage` comes from `await store.getStore('memory')`. |
