# Client SDK examples

All examples follow the current docs. Run them against `mastra dev` (`http://localhost:4111`) first.

## Contents

1. Streaming chat with memory and cancellation
2. Workflow run with polling and resume
3. Authenticated server-side call with request context
4. OpenAI-compatible Responses API

---

## 1. Streaming chat with memory and cancellation

```typescript
// lib/mastra-client.ts
import { MastraClient } from '@mastra/client-js'

export const mastraClient = new MastraClient({
  baseUrl: process.env.MASTRA_API_URL || 'http://localhost:4111',
  retries: 3,
  backoffMs: 300,
  maxBackoffMs: 5000,
})
```

```typescript
// chat.ts
import { mastraClient } from './lib/mastra-client'

export async function ask(prompt: string, onText: (text: string) => void, signal: AbortSignal) {
  const agent = mastraClient.getAgent('support-agent')

  try {
    const response = await agent.stream(prompt, {
      memory: { thread: 'thread-abc', resource: 'user-123' },
      abortSignal: signal,
    })

    await response.processDataStream({
      onChunk: async chunk => {
        if (chunk.type === 'text-delta') onText(chunk.payload.text)
        if (chunk.type === 'tool-call') console.log('tool', chunk.payload.toolName)
      },
    })
  } catch (error) {
    console.error('An error occurred:', (error as Error).message)
  }
}

// Usage
const controller = new AbortController()
void ask('Where is my order?', t => process.stdout.write(t), controller.signal)
// Later, when the user presses Stop:
controller.abort()
```

Load earlier messages for the UI:

```typescript
const thread = mastraClient.getMemoryThread({ threadId: 'thread-abc', agentId: 'support-agent' })
const { messages, hasMore } = await thread.listMessages({ page: 0, perPage: 20 })
```

---

## 2. Workflow run with polling and resume

```typescript
import { mastraClient } from './lib/mastra-client'

const workflow = mastraClient.getWorkflow('city-workflow')

// Await the whole run
const run = await workflow.createRun({ resourceId: 'user-123' })
const result = await run.startAsync({ inputData: { city: 'New York' } })
console.log(result)

// Fire and forget, then poll
const bgRun = await workflow.createRun()
await bgRun.start({ inputData: { city: 'Paris' } })
const status = await workflow.runById(bgRun.runId, { fields: ['status', 'result'] })

// Resume a suspended step later
if (status.status === 'suspended') {
  const resumed = await workflow.createRun({ runId: bgRun.runId })
  await resumed.resumeAsync({ step: 'approve', resumeData: { approved: true } })
}

// Stream progress
const streamRun = await workflow.createRun()
const stream = await streamRun.stream({ inputData: { city: 'Berlin' } })
for await (const chunk of stream) {
  console.log(JSON.stringify(chunk, null, 2))
}
```

---

## 3. Authenticated server-side call with request context

```typescript
import { MastraClient, RequestContext } from '@mastra/client-js'

const client = new MastraClient({
  baseUrl: process.env.MASTRA_API_URL!,
  headers: {
    Authorization: `Bearer ${process.env.MASTRA_JWT_TOKEN}`,
  },
})

const requestContext = new RequestContext()
requestContext.set('userId', 'user-123')

const agent = client.getAgent('support-agent')
const response = await agent.generate('Summarize this ticket', { requestContext })
console.log(response.text)
```

In a browser that signs in with cookies on another origin, replace `headers` with `credentials: 'include'`. The server must allow credentials for that exact origin.

Re-stream an agent response from your own route (for example a framework action):

```typescript
export async function action() {
  const agent = client.getAgent('support-agent')
  const stream = await agent.stream('Hello')
  return new Response(stream.body)
}
```

---

## 4. OpenAI-compatible Responses API

```typescript
import { MastraClient } from '@mastra/client-js'

const client = new MastraClient({ baseUrl: 'http://localhost:4111' })

const first = await client.responses.create({
  agent_id: 'support-agent',
  input: 'Start a support thread',
  store: true,
})
console.log(first.output_text)

// Continue in the same memory thread
const second = await client.responses.create({
  agent_id: 'support-agent',
  conversation_id: first.conversation_id!,
  input: 'Add a follow-up to the same thread',
  store: true,
})

// Stream
const stream = await client.responses.create({
  agent_id: 'support-agent',
  input: 'Summarize this ticket',
  stream: true,
})
for await (const event of stream) {
  if (event.type === 'response.output_text.delta') process.stdout.write(event.delta)
}

// Inspect the stored thread
const items = await client.conversations.items.list(first.conversation_id!)
```

This API is experimental. Pin the client and server versions together.
