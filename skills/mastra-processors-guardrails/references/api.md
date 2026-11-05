# Processor API reference

Distilled from `https://mastra.ai/reference/processors/processor-interface.md` and `https://mastra.ai/docs/agents/processors.md`. Verify against the installed version.

## Contents

- Agent and call options
- Default error processors
- Processor interface
- Method arguments and returns
- Abort, tripwire, and retries
- Violations
- Custom stream chunks
- Processor workflows

---

## Agent and call options

| Option | Where | Notes |
|---|---|---|
| `inputProcessors` | Agent, call | Array or `({ requestContext }) => array`. Per-call value replaces the agent's array. |
| `outputProcessors` | Agent, call | Same. |
| `errorProcessors` | Agent, call | Agent list merges with defaults. Per-call list replaces the resolved list, defaults included. |
| `errorProcessorDefaults` | Agent | `false` disables the four default error processors. |
| `maxProcessorRetries` | Agent, call | Cap for `abort(..., { retry: true })` in `processInputStep`/`processOutputStep`. Unset by default, which disables those retries. |
| `prepareStep` | Call | Shorthand for `processInputStep`. Same arguments and return type. |

Memory, workspace, and other framework processors still run around your arrays.

---

## Default error processors

Added to every agent unless your list already has the same `id`, in this order:

1. `ProviderHistoryCompat`: rewrites provider-incompatible history in the outbound prompt
2. `PrefillErrorHandler`: recovers from assistant prefill rejections (Anthropic)
3. `UnsupportedFileHandler`: removes a rejected file, uploads it to the sandbox if any, retries
4. `StreamErrorRetryProcessor`: retries transient API and stream failures (`maxRetries` default 1)

Error processors stop at the first `{ retry: true }`. Without `maxProcessorRetries`, error-processor retries stop after 3. Customize one by passing an instance with the same `id`:

```typescript
errorProcessors: [new StreamErrorRetryProcessor({ maxRetries: 5 })],
maxProcessorRetries: 5,
```

---

## Processor interface

Import types from `@mastra/core/processors`.

```typescript
interface Processor<TId extends string = string> {
  readonly id: TId
  readonly name?: string
  readonly description?: string
  processDataParts?: boolean // processOutputStream also receives data-* chunks
  onViolation?: (violation: ProcessorViolation) => void | Promise<void>

  processInput?(args): ProcessInputResult | Promise<ProcessInputResult>
  processInputStep?(args): ProcessInputStepResult | MessageList | MastraDBMessage[] | void
  processLLMRequest?(args): ProcessLLMRequestResult
  processLLMResponse?(args): ProcessLLMResponseResult
  processAPIError?(args): ProcessAPIErrorResult | void
  processOutputStream?(args): Promise<ChunkType | null | undefined>
  processOutputStep?(args): ProcessorMessageResult
  processToolResult?(args): ProcessorMessageResult
  processOutputResult?(args): ProcessorMessageResult
}
```

Type aliases: `InputProcessor` (needs `processInput`, `processInputStep`, `processLLMRequest`, or `processLLMResponse`), `OutputProcessor` (needs `processOutputStream`, `processOutputStep`, or `processOutputResult`), `ErrorProcessor` (needs `processAPIError`). Tracing options: `spanType`, `spanName`, `spanAttributes`.

### Timing

| Method | Frequency |
|---|---|
| `processInput` | Once per initial request. Resuming from a durable snapshot may skip it. |
| `processInputStep` | Once per model step, before the provider request |
| `processLLMRequest` | Once per provider call. Changes are transient. |
| `processOutputStream` | Per streamed chunk |
| `processLLMResponse` | Once per completed provider stream |
| `processOutputStep` | Once per model step, before local tools run |
| `processToolResult` | Per tool result, before it enters the message list. Not called when `execute` throws. |
| `processAPIError` | On eligible provider API errors |
| `processOutputResult` | Once at finalization |

---

## Method arguments and returns

Common arguments: `messages` (snapshot of `MastraDBMessage[]`), `messageList` (live `MessageList`), `abort`, `retryCount`, `tracingContext`, `requestContext`. Output methods also get `state` (per processor, per request) and `writer`.

Message text lives in `message.content.parts`. Filter `part.type === 'text'`. `message.content.content` is a legacy fallback.

### `processInput`

Extra args: `systemMessages`. Return `MastraDBMessage[]`, the same `messageList`, or `{ messages, systemMessages }`.

### `processInputStep`

Args: `messages`, `messageList`, `runId`, `stepNumber` (0-indexed), `steps`, `systemMessages`, `model`, `toolChoice`, `activeTools`, `tools`, `providerOptions`, `modelSettings`, `structuredOutput`, `sendSignal`.

Return any of: `model` (instance or router string), `toolChoice`, `activeTools`, `tools`, `messages` or `messageList` (not both), `systemMessages` (this step only), `providerOptions`, `modelSettings`, `structuredOutput`.

`toolChoice: 'none'` still sends tool definitions. They are only dropped when the step also sends a structured output schema.

### `processLLMRequest` / `processLLMResponse`

Request args: `prompt` (provider format), `model`, `stepNumber`, `steps`, `state`. Changes do not persist to memory or history. `abort()` emits a tripwire.

Response args: `chunks`, `model`, `stepNumber`, `steps`, `state` (same object as the request hook), `fromCache`. Skip cache writes when `fromCache` is true.

### `processOutputStream`

Args: `part`, `streamParts`, `state`, `messageList`, `writer`. Return a chunk to emit it. `null` or `undefined` drops it. Call `abort()` to stop the stream.

### `processOutputStep`

Args: `messages`, `stepNumber`, `finishReason`, `providerMetadata`, `toolCalls`, `text`, `usage`, `systemMessages`, `steps`, `state`. Return `messages` to keep the conversation. Returning `[]` empties it.

### `processToolResult`

Args: `toolName`, `toolCallId`, `args`, `result`, `providerExecuted`, `messages`, `messageList`, `stepNumber`, `steps`, `state`. Replace the result with `messageList.updateToolInvocation({...})`. Streaming clients see the processed value.

### `processOutputResult`

Args: `messages`, `state`, `result` (`text`, `usage`, `finishReason`, `steps`), `writer`. Add metadata to `msg.content.metadata`; read it from `result.response?.uiMessages`.

### `processAPIError`

Args: `error`, `messages`, `messageList`, `stepNumber`, `steps`, `state`, `retryCount`, `abort`, `writer`, `abortSignal`. Return `{ retry: true }` after fixing the request. Attachment download failures arrive as `MastraError` id `DOWNLOAD_ASSETS_FAILED` with `error.details.url`.

---

## Abort, tripwire, and retries

```typescript
abort('Blocked content detected', { retry: false, metadata: { category: 'pii' } })
```

Tripwire chunk:

```typescript
type TripwireChunk = {
  type: 'tripwire'
  runId: string
  from: 'AGENT'
  payload: { reason: string; retry?: boolean; metadata?: unknown; processorId: string }
}
```

- `generate()` exposes `result.tripwire` and `finishReason: 'other'`.
- `retry: true` replays the step with the reason appended as a system reminder. Requires `maxProcessorRetries`.
- The default cap of 3 applies only to `processAPIError` retries.

---

## Violations

`onViolation` receives `{ processorId, message, detail }`. The runner calls it when a processor aborts. `RegexFilterProcessor` also calls it on redaction, and `TokenCostControl` on warnings. It does not fire for `processToolResult` aborts, processor workflows while streaming output, or log-only strategies such as `ModerationProcessor` `warn`. Errors inside it are caught.

---

## Custom stream chunks

```typescript
await writer?.custom({ type: 'data-moderation-update', data: { reason } })
```

Types must start with `data-`. `processOutputStream` skips `data-*` chunks unless `processDataParts = true`.

---

## Processor workflows

Build with `createWorkflow({ id, inputSchema: ProcessorStepSchema, outputSchema: ProcessorStepSchema })`, wrap processors with `createStep(processor)`, and use `.parallel()` plus `.map()`. Branch results are keyed `processor:<id>`. Registered agents register their processor workflows, so they appear in Studio.

---

## Signals from processors

`sendSignal({ type: 'reactive', contents, attributes?, metadata?, transient? })` in `processInputStep` delivers a `<system-reminder>` message. `transient: true` sends it for the current call only, without storing it. See `mastra-signals`.
