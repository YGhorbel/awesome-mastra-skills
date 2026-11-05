# Client SDK API reference

Distilled from the pages under `https://mastra.ai/reference/client-js/` and `https://mastra.ai/docs/server/mastra-client.md`. Verify against the installed `@mastra/client-js` types.

## Contents

- Constructor
- Top-level methods
- Agent handle
- Workflow handle
- Memory
- Tools and vectors
- Logs, traces, scores, feedback
- Datasets and experiments
- Responses and Conversations
- Agent controller
- Errors and cancellation

---

## Constructor: `new MastraClient({...})`

Import: `import { MastraClient, RequestContext, createTool } from '@mastra/client-js'`

| Option | Type | Default | Notes |
|---|---|---|---|
| `baseUrl` | `string` | | Server origin, for example `http://localhost:4111`. |
| `apiPrefix` | `string` | `/api` | Match a custom `server.apiPrefix`. |
| `retries` | `number` | `3` | Retries before throwing. |
| `backoffMs` | `number` | `300` | Initial backoff, doubled per retry. |
| `maxBackoffMs` | `number` | `5000` | Backoff cap. |
| `headers` | `Record<string, string>` | | Sent with every request (auth, diagnostics). |
| `credentials` | `'omit' \| 'same-origin' \| 'include'` | | Use `'include'` for cross-origin session cookies. |
| `abortSignal` | `AbortSignal` | | Cancels every request tied to it. |

`requestContext` on calls accepts a `RequestContext` instance (from `@mastra/client-js`) or a `Record<string, any>`.

---

## Top-level methods

| Method | Returns |
|---|---|
| `listAgents()` | Record of agent ID to serialized config |
| `getAgent(agentId)` | Agent handle |
| `listWorkflows()`, `getWorkflow(id)` | Workflows |
| `listWorkflowRunCounts()` | `Record<string, { running, suspended }>` keyed by registry key |
| `listTools()`, `getTool(id)` | Tools |
| `getVector(name)` | Vector handle |
| `listMemoryThreads({ resourceId, agentId? })` | Threads |
| `createMemoryThread({ title, metadata, resourceId, agentId })` | Thread |
| `getMemoryThread({ threadId, agentId })` | Thread handle |
| `saveMessageToMemory({ messages, agentId })` | `{ messages }` |
| `getWorkingMemory({ agentId, threadId, resourceId? })` | `{ workingMemory, source }` |
| `getMemoryStatus()` | Memory status |
| `listLogs({ transportId })`, `getLogForRun({ runId, transportId })`, `listLogTransports()` | Logs |
| `getTrace(traceId)`, `getTraces(params)`, `listTracesLight(params)`, `deleteTraces(params)` | Traces |
| `listAgentControllers()`, `getAgentController(key)` | Agent controllers |
| `resumeBackgroundTask(id, resumeData, { suspendedAt })` | Background task (409 if state changed) |
| `listStoredAgents(params)`, `createStoredAgent(config)`, `getStoredAgent(id)` | Stored agents |
| `listDynamicWorkflows(params)`, `upsertDynamicWorkflow(def)`, `getDynamicWorkflow(id)` | Dynamic workflows (beta) |

---

## Agent handle: `client.getAgent(id)`

| Method | Notes |
|---|---|
| `details()` | Agent config. |
| `generate(messages, options)` | `messages`: string or `{ role, content }[]`. Options include `memory: { thread, resource }`, `requestContext`, `structuredOutput`, `clientTools`, `requireToolApproval`, `runId`, `abortSignal`. |
| `stream(messages, options)` | Same options. Returns a response with `processDataStream({ onChunk })` and `body`. |
| `streamUntilIdle(messages, { memory, maxIdleMs })` | Keeps the stream open until background tasks finish. Needs memory. |
| `network(messages)` | Agent network stream (deprecated pattern on the server side). |
| `sendMessage({ message, resourceId, threadId })` | Send to an active or idle thread. Returns `{ runId }`. |
| `queueMessage(...)`, `queueSignal(...)`, `sendSignal(...)` | Queue input or signals for the thread. |
| `subscribeToThread({ resourceId, threadId, withRunStatus?, withInitialHistory? })` | Returns `processDataStream({ onChunk, reconnect })`, `abort()`, `unsubscribe()`. |
| `abortRun(runId)` | Durable agents only. Returns `{ aborted }`. |
| `abortThread({ resourceId, threadId, clearPendingSignals? })` | Returns `{ aborted }`. |
| `cancelQueuedMessages({ resourceId, threadId, signalIds })` | Returns `{ cancelledSignalIds }`. |
| `listSuspendedRuns({ threadId?, resourceId?, fromDate?, toDate?, page?, perPage? })` | `{ runs, total }`. Each run has `toolCalls`. |
| `approveToolCall({ runId, toolCallId })`, `declineToolCall({ runId, toolCallId, reason? })` | Return continuation streams. |
| `sendToolApproval({ resourceId, threadId, toolCallId, approved })` | Resumes through an existing thread subscription. |
| `approveToolCallGenerate(...)`, `declineToolCallGenerate(...)` | Non-streaming variants. |
| `resumeStream(resumeData, { runId, toolCallId? })` | Resume a suspended stream with custom data. |
| `getTool(toolId)`, `executeTool(toolId, { data })` | Agent tools. |
| `createSchedule`, `listSchedules`, `getSchedule`, `updateSchedule`, `deleteSchedule`, `runSchedule`, `pauseSchedule`, `resumeSchedule`, `listScheduleTriggers` | Agent schedules (see `mastra-schedules`). |

Stream chunk shapes: `chunk.type === 'text-delta'` with `chunk.payload.text`; `'tool-call'` with `chunk.payload.toolName` and `chunk.payload.args`.

Client tools: `createTool({ id, description, inputSchema, outputSchema?, execute, toModelOutput? })` from `@mastra/client-js`. `execute(inputData, { observe })` can add spans with `observe.span()` and logs with `observe.log()`.

---

## Workflow handle: `client.getWorkflow(id)`

| Method | Notes |
|---|---|
| `details()` | Workflow info. |
| `createRun({ runId?, resourceId? })` | Returns a run. |
| `run.startAsync({ inputData, initialState? })` | Waits for the result. |
| `run.start({ inputData })` | Fire and forget. Poll with `workflow.runById(run.runId)`. |
| `run.stream({ inputData })` | Async iterable of chunks. |
| `run.resumeAsync({ step, resumeData, forEachIndex? })`, `run.resume(...)` | Resume a suspended step. |
| `run.cancel()` | Returns `{ message: 'Workflow run canceled' }`. |
| `runById(runId, { fields?, withNestedWorkflows?, requestContext? })` | Run result: `runId`, `status`, `payload`, `result`, `error`, `steps`, timestamps. |

---

## Memory thread handle

| Method | Notes |
|---|---|
| `get()`, `update({ title, metadata, resourceId })`, `delete()` | Thread CRUD. |
| `clone({ newThreadId?, title?, metadata?, options: { messageLimit?, messageFilter? } })` | Returns `{ thread, clonedMessages }`. |
| `listMessages({ page?, perPage?, orderBy?, filter: { metadata } })` | Returns `{ messages, total, hasMore }`. Metadata filters match shallow scalars with AND. |
| `deleteMessages(id \| id[])` | Returns `{ success, message }`. |

---

## Tools and vectors

- `tool.details()`, `tool.execute({ args, threadId?, resourceId? })`
- `vector.details(indexName)`, `vector.createIndex({ indexName, dimension, metric })` (`cosine`, `euclidean`, `dotproduct`), `vector.upsert({ indexName, vectors, metadata, ids? })`, `vector.query({ indexName, queryVector, topK, filter?, includeVector? })`, `vector.getIndexes()`, `vector.delete(indexName)`

---

## Logs, traces, scores, feedback

- `getTraces({ pagination: { page, perPage, dateRange }, filters: { name, spanType, entityId, entityType } })`
- `listTracesLight(...)` returns preview fields only. Fetch full traces with `getTrace(traceId)`.
- `score({ scorerName, targets: [{ traceId, spanId? }] })`, `listScoresBySpan({ traceId, spanId, page, perPage })`, `createScore({ score: { traceId, spanId?, scorerId, score } })`
- `createFeedback({ feedback: { traceId, spanId?, feedbackSource, feedbackType, value, comment? } })` plus list, aggregate, and delete methods (see `mastra-observability`)

---

## Datasets and experiments

| Method | Notes |
|---|---|
| `createDatasetExperiment({ datasetId, id?, targetType?, targetId?, scorerIds?, version? })` | Idempotent on `id`. Returns `{ experimentId, status, totalItems, datasetVersion }`. |
| `runExperimentItem({ datasetId, experimentId, itemId, attempt?, requestContext? })` | Runs the target server-side. Returns `{ result, scores }`. |
| `submitExperimentResult(...)` | For target-less ingestion. |
| `finalizeExperiment({ datasetId, experimentId })` | Computes counts. |
| `getExperiment`, `deleteExperiment`, `deleteDatasetExperiment`, `purgeDatasetItem` | Management. |

See `mastra-datasets-experiments`.

---

## Responses and Conversations (experimental)

- `client.responses.create({ agent_id, input, store?, stream?, conversation_id?, previous_response_id?, model? })`: returns `output_text`, `id`, `conversation_id`. With `stream: true`, iterate events such as `response.output_text.delta`.
- `client.responses.stream(params)`, `retrieve(responseId)`, `delete(responseId)`
- `client.conversations.create({ agent_id, title? })`, `retrieve(id)`, `delete(id)`, `items.list(id)`. `conversation_id` is the raw memory thread ID.

---

## Agent controller

`client.getAgentController(key)` uses the registration key from `new Mastra({ agentControllers })`, not the controller's `id`.

- Controller: `listModes()`, `listModels()`, `listActiveRuns()`, `workspaceStatus()`, `session(sessionId)`
- Session: `create({ resourceId?, tags?, threadId? })`, `subscribe({ onEvent, onError, onReconnect, reconnect, idleTimeoutMs })`, `sendMessage`, `steer`, `followUp`, `abort`, `approveTool(toolCallId, approved)`, `respondToToolSuspension(toolCallId, resumeData)`, `state()`, `setState()`, `switchMode()`, `switchModel()`, `listThreads()`, `switchThread()`, `createThread()`
- Missed events are not replayed after reconnect. Re-sync from `onReconnect` with `session.state()`.

---

## Errors and cancellation

- Every method can throw. Catch and read `error.message`.
- Reconnecting streams stop on 4xx (except 408 and 429) or 501 and reject with `MastraClientError`.
- Cancel one call with `abortSignal`, or `await reader.cancel()` on `response.body.getReader()`.
- Client-wide `abortSignal` in the constructor cancels all requests on it.
