# Streaming examples

All examples follow the current docs. Verify before copying into a project on an older version.

## Contents

1. Chunk router with abort, timeout, and callbacks
2. Tool progress with writer.custom and transient chunks
3. Workflow streaming with an agent step
4. Smoothed output in an AI SDK route

---

## 1. Chunk router with abort, timeout, and callbacks

```typescript
import { mastra } from '../src/mastra/index.ts'

const agent = mastra.getAgentById('test-agent')
const controller = new AbortController()
setTimeout(() => controller.abort(), 30_000)

const stream = await agent.stream('Summarize this repo', {
  maxSteps: 5,
  abortSignal: controller.signal,
  modelSettings: {
    timeout: {
      totalMs: 30000, // fail the run if it takes longer than 30s
      stepMs: 10000, // fail an individual model call after 10s
      firstChunkMs: 3000, // fail a model call that produces no content within 3s
    },
  },
  onError: ({ error }) => {
    console.error('Streaming error:', error)
  },
  onAbort: ({ steps, text }) => {
    console.log('Stream aborted after', steps.length, 'steps')
    console.log('Partial text:', text)
  },
})

try {
  for await (const chunk of stream.fullStream) {
    switch (chunk.type) {
      case 'text-delta':
        process.stdout.write(chunk.payload.text)
        break
      case 'tool-call':
        console.log(`\n[tool] ${chunk.payload.toolName}`, chunk.payload.args)
        break
      case 'tool-result':
        console.log(`[tool result] ${chunk.payload.toolName}`, chunk.payload.result)
        break
      case 'step-finish':
        console.log('\n[step finished]')
        break
      case 'abort':
        console.log('\n[aborted]')
        break
      case 'finish':
        console.log('\nDone:', chunk.payload.stepResult.reason)
        console.log('Usage:', chunk.payload.output.usage)
        break
      case 'error':
        console.error('Error:', chunk.payload.error)
        break
    }
  }
} catch (error) {
  // Thrown stopWhen predicates and timeouts surface here
  console.error('Stream failed:', error)
}

const output = await stream.getFullOutput()
console.log({ finishReason: output.finishReason, usage: output.usage })
```

Structured output streams partial objects instead:

```typescript
import { z } from 'zod'

const stream = await agent.stream('Generate user data', {
  structuredOutput: {
    schema: z.object({ name: z.string(), age: z.number(), email: z.string() }),
  },
})

for await (const partial of stream.objectStream) {
  console.log('Progress:', partial) // { name: "John" }, { name: "John", age: 30 }, ...
}
const user = await stream.object
```

---

## 2. Tool progress with writer.custom and transient chunks

```typescript
// src/mastra/tools/build-tool.ts
import { createTool } from '@mastra/core/tools'
import { z } from 'zod'

export const buildTool = createTool({
  id: 'build-tool',
  description: 'Builds the project and reports progress',
  inputSchema: z.object({ target: z.string() }),
  outputSchema: z.object({ ok: z.boolean() }),
  execute: async (inputData, context) => {
    await context?.writer?.custom({
      type: 'data-tool-progress',
      status: 'pending',
    })

    for (let i = 1; i <= 12; i++) {
      await context?.writer?.custom({
        type: 'data-build-log',
        data: { line: `Compiling module ${i} of 12...` },
        transient: true, // live only, not saved to message history
      })
    }

    await context?.writer?.custom({
      type: 'data-tool-progress',
      status: 'success',
    })

    return { ok: true }
  },
})
```

Consume the custom chunks next to normal chunks:

```typescript
const stream = await agent.stream('Build the web target')

for await (const chunk of stream.fullStream) {
  if (chunk.type === 'data-build-log') console.log(chunk)
  if (chunk.type === 'data-tool-progress') console.log(chunk)
  if (chunk.type === 'text-delta') process.stdout.write(chunk.payload.text)
}
```

Every `writer` call is awaited. A missing `await` locks the stream (`WritableStream is locked`).

---

## 3. Workflow streaming with an agent step

```typescript
// src/mastra/workflows/weather-workflow.ts
import { createStep, createWorkflow } from '@mastra/core/workflows'
import { z } from 'zod'

const forecastStep = createStep({
  id: 'forecast',
  inputSchema: z.object({ city: z.string() }),
  outputSchema: z.object({ value: z.string() }),
  execute: async ({ inputData, mastra, writer }) => {
    await writer.write({ type: 'custom-event', status: 'pending' })

    const testAgent = mastra?.getAgent('testAgent')
    const stream = await testAgent?.stream(`What is the weather in ${inputData.city}?`)

    // Forward partial text to the workflow stream and aggregate usage
    await stream!.textStream.pipeTo(writer!)

    return { value: await stream!.text }
  },
})

export const weatherWorkflow = createWorkflow({
  id: 'weather-workflow',
  inputSchema: z.object({ city: z.string() }),
  outputSchema: z.object({ value: z.string() }),
})
  .then(forecastStep)
  .commit()
```

```typescript
const run = await mastra.getWorkflow('weatherWorkflow').createRun()

const stream = run.stream({ inputData: { city: 'Tokyo' } })

for await (const chunk of stream) {
  console.log(chunk.type, chunk.payload)
}

const result = await stream.result
const usage = await stream.usage
console.log(result.status, usage)
```

Reattach to a run that is still going, or resume a suspended one:

```typescript
const observed = await run.observeStream()
for await (const chunk of observed) console.log(chunk)

if (result.status === 'suspended') {
  const resumed = await run.resumeStream({ resumeData: { value: 'resume data' } })
  for await (const chunk of resumed) console.log(chunk)
}
```

---

## 4. Smoothed output in an AI SDK route

Pace uneven token output word by word before converting to AI SDK UI chunks:

```typescript
// app/api/chat/route.ts
import { handleChatStream, smoothStream } from '@mastra/ai-sdk'
import { createUIMessageStreamResponse } from 'ai'
import { mastra } from '@/src/mastra'

export async function POST(req: Request) {
  const params = await req.json()
  const stream = await handleChatStream({
    mastra,
    agentId: 'weatherAgent',
    params,
    experimentalTransform: smoothStream({
      delayInMs: 20,
      chunking: 'word',
    }),
  })

  return createUIMessageStreamResponse({ stream })
}
```

Outside a route, pipe the core transform directly:

```typescript
import { smoothStream } from '@mastra/core/stream'

const result = await agent.stream('Explain how rainbows form')
const smoothed = result.fullStream.pipeThrough(
  smoothStream({ delayInMs: 20, chunking: new Intl.Segmenter('ja', { granularity: 'word' }) }),
)

for await (const chunk of smoothed) {
  if (chunk.type === 'text-delta') process.stdout.write(chunk.payload.text)
}
```

`result.text` and `onChunk` keep the model's original timing. See `mastra-agentic-ui` for the frontend side.
