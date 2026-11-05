# Streaming checklist

Run this before calling a streaming feature done.

## Consumption

- [ ] Exactly one consumer per stream view (`textStream`, `fullStream`, or `objectStream`)
- [ ] Promise properties (`text`, `usage`, `object`) are awaited after consumption, or `consumeStream()` is called
- [ ] Chunk handlers read fields from `chunk.payload`
- [ ] Unknown chunk types are ignored, not treated as errors

## Bounds and cancellation

- [ ] `maxSteps` or `stopWhen` set
- [ ] `modelSettings.timeout` set for user-facing paths (`totalMs`, `stepMs`, `firstChunkMs`)
- [ ] `abortSignal` wired to client disconnect or a cancel button
- [ ] The `abort` chunk or `onAbort` updates the UI state
- [ ] Tools are safe to abort mid-run (abort is cooperative)

## Errors

- [ ] Consumption wrapped in `try/catch` (a throwing `stopWhen` rejects `fullStream`)
- [ ] `onError` or `consumeStream({ onError })` logs failures
- [ ] `MastraTimeoutError` handled with a user-facing message
- [ ] A `finish` chunk with `stepResult.reason === 'error'` is treated as failure

## Custom chunks

- [ ] Every `writer.write()` and `writer.custom()` call is awaited
- [ ] Custom chunk types use the `data-` prefix when the UI reads them
- [ ] High-frequency or large chunks set `transient: true`
- [ ] Output processors that must see `data-*` chunks set `processDataParts = true`

## Workflows

- [ ] Workflow runs stream through `run.stream()` and read `result` at the end
- [ ] Agent steps pipe `textStream` into `writer` when partial text should reach the client
- [ ] Reconnect path uses `run.observeStream()` or `run.resumeStream()`

## Integration

- [ ] AI SDK frontends receive `toAISdkStream()` or `handleChatStream()` output with the installed AI SDK version (see `mastra-agentic-ui`)
- [ ] Background-task agents use `untilIdle` with memory, not `streamUntilIdle()`
- [ ] No new code uses `.network()` events or `streamLegacy()` with V2 models
