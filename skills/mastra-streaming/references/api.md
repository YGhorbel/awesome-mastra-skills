# Streaming API reference

Distilled from `https://mastra.ai/reference/streaming/agents/stream.md`, `https://mastra.ai/reference/streaming/agents/MastraModelOutput.md`, `https://mastra.ai/reference/streaming/ChunkType.md`, `https://mastra.ai/reference/streaming/smoothStream.md`, the workflow stream references, and `https://mastra.ai/docs/guides/streaming.md`. Verify against the installed version before relying on an option.

## Contents

- agent.stream() options (streaming-relevant)
- MastraModelOutput
- Chunk catalog
- Writer API
- smoothStream()
- Workflow streams
- Deprecated and legacy APIs

---

## `agent.stream(messages, options)`

`messages`: `string | string[] | CoreMessage[] | AiMessageType[] | UIMessageWithMetadata[]`. Returns `MastraModelOutput` (plus `traceId`/`spanId` when tracing is on). Designed for V2 models.

| Option | Notes |
|---|---|
| `maxSteps` / `stopWhen` | Bound the loop. A throwing `stopWhen` rejects `fullStream` with no `finish` or `error` chunk. |
| `modelSettings.timeout` | `{ totalMs, stepMs, firstChunkMs }`. Exceeding fails with `MastraTimeoutError` (`timeoutType`: `'total' \| 'step' \| 'firstChunk'`). `stepMs` and `firstChunkMs` advance to the next fallback model, `totalMs` does not. |
| `modelSettings.maxOutputTokens` | Not `maxTokens`. |
| `abortSignal` | Cooperative cancel, including in-flight subagents. Emits an `abort` chunk. Status ends canceled with an `aborted` finish reason. Streamed text is saved when memory is writable. |
| `onChunk(chunk)` | Every chunk. |
| `onStepFinish(step)` | After each step. Unavailable with structured output. |
| `onFinish(result)` | When streaming completes. |
| `onError({ error })` | Stream errors. |
| `onAbort({ steps, text })` | Completed steps and the in-flight step's text so far. |
| `structuredOutput` | Enables `objectStream`/`object`. See `mastra-structured-output`. |
| `includeRawChunks` | Include provider `raw` chunks where supported. |
| `experimentalTransform` | A transform factory, such as `smoothStream()` from `@mastra/ai-sdk`. |
| `hideSignals` | `true`, `false`, or an array of `user`, `state`, `reactive`, `notification`, `user-message`, `system-reminder`. Filters this caller's `fullStream` only. |
| `untilIdle` | `true` or `{ maxIdleMs }`. Keeps the stream open across background-task continuations. Requires memory. Default idle 5 minutes. |
| `eagerToolExecution` | Default `true`. Tool calls start when their arguments finish streaming. |
| `savePerStep` | Persist messages after each step. Default `false`. |
| `providerOptions.openai.transport` | `'websocket' \| 'fetch' \| 'auto'` for Responses WebSocket streaming. Close a kept-open socket with `stream.transport?.close()`. |

All other agent execution options (`memory`, `requestContext`, `toolChoice`, `delegation`, and so on) also apply. See `mastra-agents`.

---

## `MastraModelOutput`

### Streams

| Property | Type | Notes |
|---|---|---|
| `fullStream` | `ReadableStream<ChunkType<OUTPUT>>` | Every chunk |
| `textStream` | `ReadableStream<string>` | Text deltas only |
| `objectStream` | `ReadableStream<Partial<OUTPUT>>` | Partial objects with a schema |
| `elementStream` | `ReadableStream<element>` | Array elements as each completes, when the schema is an array |

### Promises (resolve when the run ends)

| Property | Type |
|---|---|
| `text` | `Promise<string>` |
| `object` | `Promise<OUTPUT>` (validated, rejects on failure) |
| `reasoning` | `Promise<string>` (empty string without reasoning) |
| `reasoningText` | `Promise<string \| undefined>` |
| `toolCalls` | `Promise<ToolCallChunk[]>` |
| `toolResults` | `Promise<ToolResultChunk[]>` |
| `usage` | `Promise<{ inputTokens, outputTokens, totalTokens, reasoningTokens?, cachedInputTokens? }>` |
| `finishReason` | `Promise<string \| undefined>` (`stop`, `length`, `tool_calls`, `content_filter`, ...) |
| `response` | `Promise<{ id, timestamp, modelId, headers, messages, uiMessages }>` |

`error`: `Error | undefined` after a failed run.

### Methods

| Method | Notes |
|---|---|
| `getFullOutput()` | `Promise<{ text, object, toolCalls, toolResults, usage, reasoning, finishReason, response }>` |
| `consumeStream({ onError? })` | Drain the stream without handling chunks, so promises resolve |

---

## Chunk catalog

Base fields on every chunk: `type`, `runId`, `from`, and `traceId` when tracing is on (not on custom `data-*` chunks).

| Group | Type | Key payload fields |
|---|---|---|
| Text | `text-start`, `text-delta`, `text-end` | `id`, `text` (delta) |
| Reasoning | `reasoning-start`, `reasoning-delta`, `reasoning-end`, `reasoning-signature` | `id`, `text`, `signature` |
| Tools | `tool-call` | `toolCallId`, `toolName`, `title`, `args`, `providerExecuted` |
| | `tool-result` | `toolCallId`, `toolName`, `result`, `isError`, `args` |
| | `tool-call-input-streaming-start`, `tool-call-delta`, `tool-call-input-streaming-end` | `toolCallId`, `toolName`, `argsTextDelta` |
| | `tool-error` | `toolCallId`, `toolName`, `args`, `error` |
| | `tool-call-approval`, `tool-call-suspended` | Approval and suspension (see `mastra-agent-approval-hitl`) |
| Sources and files | `source`, `file`, `reasoning-file` | `sourceType`, `url`, `title`; `data`, `mimeType` |
| Control | `start`, `step-start` | `messageId`, `modelId`, `provider`, `request`, `warnings` |
| | `step-finish` | `stepResult`, `output` (usage), `totalUsage`, `response` |
| | `finish` | `stepResult.reason` (`"error"` means failed), `output.usage`, `messages`, `response.uiMessages` |
| | `error`, `abort`, `raw`, `custom` | `error`; provider data; `kind` |
| Output | `object` | Final structured object |
| | `tool-output` | `output`: nested chunk from a tool (including subagent chunks and `writer.write` values) |
| | `step-output` | `output`: nested chunk from a workflow step |
| Background tasks | `background-task-started`, `-running`, `-progress`, `-output`, `-completed`, `-failed`, `-suspended`, `-resumed`, `-cancelled` | `taskId`, `toolName`, `toolCallId`, `result`, `error` |
| Metadata | `response-metadata`, `watch`, `goal`, `tripwire` | `tripwire`: `reason`, `retry`, `metadata`, `processorId` |
| Thread subscriptions | `data-user-message-pending`, `data-user-message-cancelled`, `thread-history`, `thread-run-status` | See `mastra-signals` |
| Custom | `data-*` | Emitted with `writer.custom()` |

---

## Writer API

Tools: `execute(inputData, context)` gets `context?.writer`. Workflow steps: `execute({ inputData, writer, mastra })`.

| Call | Effect |
|---|---|
| `await writer.write(value)` | Emit a value inside the tool or step output |
| `await writer.custom({ type: 'data-<name>', ... })` | Emit a top-level `data-*` chunk |
| `transient: true` on a `custom` chunk | Stream live, skip storage persistence |

Always await. Output processors see `data-*` chunks only with `processDataParts = true` (see `mastra-processors-guardrails`). In a step, `await stream.textStream.pipeTo(writer)` forwards an agent's text and aggregates its usage into the workflow.

---

## `smoothStream(options)`

| Import | Returns |
|---|---|
| `@mastra/core/stream` | A `TransformStream` for `fullStream.pipeThrough(...)` |
| `@mastra/ai-sdk` | A reusable factory for `experimentalTransform` on `agent.stream()` or `handleChatStream()` |

| Option | Type | Notes |
|---|---|---|
| `delayInMs` | `number \| null` | Delay after each emitted chunk. `null` disables. |
| `chunking` | `'word' \| 'line' \| RegExp \| Intl.Segmenter \| (buffer) => string \| null \| undefined` | Boundary rule. A detector returns a non-empty prefix of the buffer, or nullish to wait. |

Only `text-delta` and `reasoning-delta` are re-chunked. Other chunks pass through after buffered text flushes. Experimental.

---

## Workflow streams

| Method | Returns | Notes |
|---|---|---|
| `run.stream({ inputData, requestContext, tracingOptions, closeOnSuspend })` | `WorkflowRunOutput` | Iterate it or `fullStream`. `result`, `status`, `usage`. `closeOnSuspend` default `true`. |
| `run.observeStream()` | `ReadableStream<ChunkType>` | Attach to a running run when the original stream is gone |
| `run.resumeStream({ resumeData, step, forEachIndex, requestContext })` | Stream with `status`, `result`, `usage` | Resume a suspended run. With no arguments, reopens an interrupted stream. |
| `run.timeTravelStream(...)` | Stream | See `mastra-workflow-suspend-resume` |

Workflow events: `workflow-start`, `workflow-step-start`, `workflow-step-output`, `workflow-step-progress` (foreach: `completedCount`, `totalCount`, `currentIndex`, `iterationStatus`), `workflow-step-result`, `workflow-finish` (`payload.finalWorkflowResult` on success), plus `workflow-paused`, `workflow-step-suspended`, `workflow-canceled`. Events carry `runId` and `from` at the top level.

---

## Deprecated and legacy APIs

- `streamUntilIdle()` and `resumeStreamUntilIdle()`: use `stream(..., { untilIdle: true })`.
- `streamLegacy()`: for V1 models only.
- `output` option: use `structuredOutput` without a model.
- `run.pipeTo()` / `run.pipeThrough()` on `WorkflowRunOutput`: use `run.fullStream.pipeTo(...)`.
- `.network()` events: map to standard chunks (see `mastra-multi-agent`).
