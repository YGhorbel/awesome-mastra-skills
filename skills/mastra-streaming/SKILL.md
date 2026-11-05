---
name: mastra-streaming
description: "Stream Mastra agent and workflow output: agent.stream() and its MastraModelOutput (textStream, fullStream, objectStream, text, usage, getFullOutput), chunk types and payloads, workflow run.stream() events, custom events from tools and steps through the writer API, smoothStream pacing, abort handling, timeouts, and AI SDK conversion. Use this skill whenever the user wants to show tokens as they arrive, inspect tool calls or reasoning mid-run, emit progress from a tool or workflow step, pipe an agent stream inside a workflow, cancel a running stream, or debug a WritableStream is locked error. Triggers on agent.stream, textStream, fullStream, MastraModelOutput, ChunkType, text-delta, tool-call chunk, finish chunk, run.stream, workflow-step-output, writer.write, writer.custom, data-* chunks, transient chunks, smoothStream, @mastra/core/stream, abortSignal, onChunk, consumeStream, toAISdkStream, untilIdle."
license: Apache-2.0
metadata:
  category: agents
  catalog_summary: "Agent and workflow streaming: MastraModelOutput, chunk types, writer API, smoothStream, abort, and events"
  display_order: 10
  docs: https://mastra.ai/docs/guides/streaming
---

# Mastra Streaming

Stream agent tokens and workflow events as they happen. Agents return a `MastraModelOutput` with streams and promises. Workflows return a stream of lifecycle events. Tools and steps can add their own chunks with `writer`.

---

## When to use

- Showing an agent's answer progressively in a CLI, server route, or UI
- Reacting to tool calls, tool results, reasoning, or step boundaries mid-run
- Streaming typed partial objects with `structuredOutput`
- Emitting progress or custom data from a tool's `execute` or a workflow step
- Streaming a workflow run, observing it later, or resuming its stream
- Smoothing choppy token output, aborting a run, or bounding its duration

## When NOT to use

- Agent definition and `generate()` basics (use `mastra-agents`)
- Schema design for typed output (use `mastra-structured-output`)
- Route handlers and React hooks for chat UIs (use `mastra-agentic-ui`)
- Streaming from a frontend through `@mastra/client-js` (use `mastra-client-sdk`)
- Workflow structure, suspend, and resume semantics (use `mastra-workflows` and `mastra-workflow-suspend-resume`)
- Approving tool calls from the stream (use `mastra-agent-approval-hitl`)
- Background tasks and `untilIdle` continuations in depth (use `mastra-harness`)
- Thread subscriptions and signals (use `mastra-signals`)

---

## Required inputs

- What is streamed: agent text, full event stream, structured object, or workflow events
- The consumer: terminal, HTTP response, AI SDK UI, or another stream
- Which events matter (text only, tool calls, reasoning, custom progress)
- Whether the run must be cancellable or time-bounded
- Whether custom chunks must persist in memory or stay transient

---

## The framework: one output, many views

```typescript
const agent = mastra.getAgentById('test-agent')
const stream = await agent.stream('Help me organize my day')

// 1. Text only
for await (const text of stream.textStream) process.stdout.write(text)

// 2. Promises that resolve when the run ends
const text = await stream.text
const usage = await stream.usage
const finishReason = await stream.finishReason
```

Or read every chunk:

```typescript
const stream = await agent.stream('Complex task')

for await (const chunk of stream.fullStream) {
  switch (chunk.type) {
    case 'text-delta':
      process.stdout.write(chunk.payload.text)
      break
    case 'tool-call':
      console.log(`Calling ${chunk.payload.toolName}...`)
      break
    case 'tool-result':
      console.log('Tool result:', chunk.payload.result)
      break
    case 'reasoning-delta':
      console.log(`Reasoning: ${chunk.payload.text}`)
      break
    case 'finish':
      console.log('Done:', chunk.payload.stepResult.reason, chunk.payload.output.usage)
      break
    case 'error':
      console.error('Error:', chunk.payload.error)
      break
  }
}
```

Every chunk has `type`, `runId`, `from` (`AGENT`, `USER`, `SYSTEM`, `WORKFLOW`), and usually `payload`. Pick one consumer per stream: iterate `textStream` or `fullStream`, then await promises.

### Agent vs workflow streams

| | Agent `stream()` | Workflow `run.stream()` |
|---|---|---|
| Returns | `MastraModelOutput` | `WorkflowRunOutput` |
| Iterate | `textStream`, `fullStream`, `objectStream` | the output itself or `fullStream` |
| Main events | `text-delta`, `tool-call`, `tool-result`, `step-finish`, `finish` | `workflow-start`, `workflow-step-start`, `workflow-step-output`, `workflow-step-result`, `workflow-finish` |
| Final values | `text`, `object`, `usage`, `toolCalls`, `getFullOutput()` | `result`, `status`, `usage` |

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/` and the `MastraModelOutput` and `ChunkType` types. Otherwise fetch `https://mastra.ai/docs/guides/streaming.md`, `https://mastra.ai/reference/streaming/agents/stream.md`, and `https://mastra.ai/reference/streaming/ChunkType.md`. Trust these over memory.
2. **Choose the view.** `textStream` for plain text, `fullStream` for tool and step events, `objectStream` for structured output, `run.stream()` for workflows.
3. **Bound the run.** Set `maxSteps` and `modelSettings.timeout` (`totalMs`, `stepMs`, `firstChunkMs`) for user-facing paths.
4. **Wire cancellation.** Pass an `AbortController` signal as `abortSignal` and handle the `abort` chunk or `onAbort`.
5. **Emit custom progress** from tools with `context?.writer?.write()` or `context?.writer?.custom({ type: 'data-...' })`, and from steps with `writer.write()`. Always `await` the call.
6. **Handle errors** with `try/catch` around consumption, `onError`, or `consumeStream({ onError })`.
7. **Convert for the UI** with `toAISdkStream()` when the frontend uses the AI SDK (see `mastra-agentic-ui`).
8. **Test** by logging `fullStream` once to confirm the chunk sequence, then narrow to the chunks you handle.

---

## Deep dive: writer API in tools and steps

```typescript
import { createTool } from '@mastra/core/tools'

export const buildTool = createTool({
  id: 'build',
  description: 'Builds the project',
  execute: async (inputData, context) => {
    await context?.writer?.custom({ type: 'data-tool-progress', status: 'pending' })

    await context?.writer?.custom({
      type: 'data-build-log',
      data: { line: 'Compiling module 3 of 12...' },
      transient: true, // streamed live, not saved to memory
    })

    await context?.writer?.custom({ type: 'data-tool-progress', status: 'success' })
    return { ok: true }
  },
})
```

- `writer.write(value)` nests the value inside a tool or step output chunk.
- `writer.custom({ type: 'data-...' })` emits a top-level chunk that UI frameworks read directly.
- `data-*` chunks persist with message history unless `transient: true`.
- In a workflow step, `writer` is an argument of `execute`. Pipe an agent into it with `await stream.textStream.pipeTo(writer)`. Mastra aggregates the agent's usage into the workflow run.

---

## Failure patterns

- **`WritableStream is locked`.** A `writer.write()` or `writer.custom()` call was not awaited. Await every call.
- **Nothing printed, promise never settles.** Nobody consumed the stream. Iterate a stream, or call `await stream.consumeStream()` before awaiting `text`.
- **`chunk.text` is undefined.** Payload fields live under `chunk.payload` (`chunk.payload.text`, `chunk.payload.toolName`).
- **`maxTokens` ignored.** Use `modelSettings.maxOutputTokens`.
- **`stopWhen` throws and the loop hangs.** `fullStream` rejects without a `finish` or `error` chunk. Wrap consumption in `try/catch`.
- **Abort leaves side effects.** Abort is cooperative. Running tool code may finish. Make tools idempotent and check state before retrying.
- **Smoothing changes `text` timing expectations.** `smoothStream()` only affects the piped stream. `result.text` and `onChunk` keep original timing.
- **Background results never arrive.** Plain `stream()` closes after the first turn. Use `stream(..., { untilIdle: true, memory })`. `streamUntilIdle()` is deprecated.
- **Using `.network()` event names.** They are deprecated. Map them to standard chunks (see `mastra-multi-agent`).
- **Model version mismatch error.** `stream()` targets V2 models. Legacy V1 models need `streamLegacy()`; plan an upgrade with `mastra-migrations`.

---

## Output format

A finished streaming delivery contains:

- The call site with `stream()` options (`maxSteps`, `modelSettings.timeout`, `abortSignal`) and a consumer loop
- Typed handling for each chunk type the feature depends on
- Tool or step code that awaits every `writer` call, with `transient: true` for noisy chunks
- An error path (`try/catch`, `onError`, or `consumeStream({ onError })`)
- Evidence: a logged `fullStream` sample or a test asserting the chunk sequence

---

## Reference files

- [`references/api.md`](references/api.md) - `stream()` options, `MastraModelOutput` properties and methods, chunk catalog with payloads, workflow stream methods, `smoothStream()`.
- [`references/examples.md`](references/examples.md) - Chunk router with abort and timeout, tool progress with `writer.custom`, workflow streaming with an agent step, smoothed output for an AI SDK route.
- [`references/checklist.md`](references/checklist.md) - Streaming checklist.

**Live docs**

- https://mastra.ai/docs/guides/streaming
- https://mastra.ai/reference/streaming/agents/stream
- https://mastra.ai/reference/streaming/agents/MastraModelOutput
- https://mastra.ai/reference/streaming/ChunkType
- https://mastra.ai/reference/streaming/smoothStream
- https://mastra.ai/reference/streaming/workflows/stream
- https://mastra.ai/reference/streaming/workflows/observeStream
- https://mastra.ai/reference/streaming/workflows/resumeStream
