# Agentic UI examples

All examples follow `https://mastra.ai/integrations/agentic-ui/ai-sdk-ui.md`. They assume a Mastra server on `http://localhost:4111` with `chatRoute({ path: '/chat/:agentId' })`. Add `version` if your `ai` package is v6 or v7.

## Contents

1. Tool output as a component
2. Custom progress events from a tool
3. Request data to request context
4. Resuming a suspended tool
5. Workflow progress UI

---

## 1. Tool output as a component

```typescript
// src/mastra/tools/weather-tool.ts
import { createTool } from '@mastra/core/tools'
import { z } from 'zod'

export const weatherTool = createTool({
  id: 'get-weather',
  description: 'Get current weather for a location',
  inputSchema: z.object({ location: z.string() }),
  outputSchema: z.object({
    temperature: z.number(),
    conditions: z.string(),
    location: z.string(),
  }),
  execute: async inputData => {
    const res = await fetch(
      `https://api.weatherapi.com/v1/current.json?key=${process.env.WEATHER_API_KEY}&q=${inputData.location}`,
    )
    const data = await res.json()
    return {
      temperature: data.current.temp_c,
      conditions: data.current.condition.text,
      location: data.location.name,
    }
  },
})
// Registered on the agent as tools: { weatherTool }
```

```tsx
import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport } from 'ai'
import { WeatherCard } from './weather-card'

export function Chat() {
  const { messages } = useChat({
    transport: new DefaultChatTransport({ api: 'http://localhost:4111/chat/weatherAgent' }),
  })

  return (
    <div>
      {messages.map(message => (
        <div key={message.id}>
          {message.parts.map((part, index) => {
            if (part.type === 'text') return <p key={index}>{part.text}</p>
            // Part type uses the tools object key, not the tool id
            if (part.type === 'tool-weatherTool') {
              switch (part.state) {
                case 'input-available':
                  return <p key={index}>Loading...</p>
                case 'output-available':
                  return <WeatherCard key={index} {...part.output} />
                case 'output-error':
                  return <div key={index}>Error: {part.errorText}</div>
              }
            }
            return null
          })}
        </div>
      ))}
    </div>
  )
}
```

---

## 2. Custom progress events from a tool

```typescript
import { createTool } from '@mastra/core/tools'
import { z } from 'zod'

export const taskTool = createTool({
  id: 'process-task',
  description: 'Process a task with progress updates',
  inputSchema: z.object({ task: z.string() }),
  outputSchema: z.object({ result: z.string(), status: z.string() }),
  execute: async (inputData, context) => {
    // Always await, and prefix the type with data-
    await context?.writer?.custom({
      type: 'data-tool-progress',
      data: { status: 'in-progress', message: 'Gathering information...' },
    })

    await new Promise(resolve => setTimeout(resolve, 3000))

    await context?.writer?.custom({
      type: 'data-tool-progress',
      data: { status: 'done', message: `Processed "${inputData.task}"` },
    })

    return { result: `Task "${inputData.task}" completed`, status: 'completed' }
  },
})
```

```tsx
const latestProgress = useMemo(() => {
  const all: { status: string; message: string }[] = []
  messages.forEach(m =>
    m.parts.forEach(part => {
      if (part.type === 'data-tool-progress') all.push(part.data as { status: string; message: string })
    }),
  )
  return all[all.length - 1]
}, [messages])
```

---

## 3. Request data to request context

Frontend sends extra data with each message:

```tsx
sendMessage(
  { text: inputValue },
  { body: { data: { userId: 'user123', preferences: { language: 'en' } } } },
)
```

Mastra server: copy `body.data` into request context in middleware.

```typescript
import { Mastra } from '@mastra/core'
import { chatRoute } from '@mastra/ai-sdk'

export const mastra = new Mastra({
  server: {
    apiRoutes: [chatRoute({ path: '/chat/:agentId' })],
    middleware: [
      async (c, next) => {
        const requestContext = c.get('requestContext')
        if (c.req.method === 'POST') {
          const body = await c.req.raw.clone().json()
          if (body?.data) {
            for (const [key, value] of Object.entries(body.data)) {
              requestContext.set(key, value)
            }
          }
        }
        await next()
      },
    ],
  },
})
```

Next.js route alternative:

```typescript
import { handleChatStream } from '@mastra/ai-sdk'
import { RequestContext } from '@mastra/core/request-context'
import { createUIMessageStreamResponse } from 'ai'
import { mastra } from '@/src/mastra'

export async function POST(req: Request) {
  const { messages, data } = await req.json()
  const requestContext = new RequestContext()
  for (const [key, value] of Object.entries(data ?? {})) requestContext.set(key, value)

  const stream = await handleChatStream({
    mastra,
    agentId: 'weatherAgent',
    params: { messages, requestContext },
  })
  return createUIMessageStreamResponse({ stream })
}
```

Never let client data set ownership. Derive user and resource IDs from auth (see `mastra-auth`).

---

## 4. Resuming a suspended tool

```tsx
const { messages, sendMessage } = useChat({
  transport: new DefaultChatTransport({
    api: 'http://localhost:4111/chat',
    prepareSendMessagesRequest: ({ messages, body }) => {
      const resume = body?.resume as { runId: string; resumeData: unknown } | undefined
      if (resume) {
        return { body: { messages, runId: resume.runId, resumeData: resume.resumeData } }
      }
      return { body: { messages } }
    },
  }),
})

// suspended = data of the latest data-tool-call-suspended part
sendMessage(
  { text: 'Confirmed' },
  { body: { resume: { runId: suspended.runId, resumeData: { confirmed: true } } } },
)
```

For subagent tools, the part also carries `delegatedToolCallId` and `delegatedToolName` for labeling. Keep resuming with `runId` and `toolCallId`.

---

## 5. Workflow progress UI

```typescript
import { Mastra } from '@mastra/core'
import { workflowRoute } from '@mastra/ai-sdk'
import { activitiesWorkflow } from './workflows/activities-workflow'

export const mastra = new Mastra({
  workflows: { activitiesWorkflow },
  server: {
    apiRoutes: [
      workflowRoute({ path: '/workflow/activitiesWorkflow', workflow: 'activitiesWorkflow' }),
    ],
  },
})
```

```tsx
import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport } from 'ai'
import type { WorkflowDataPart } from '@mastra/ai-sdk'

type WorkflowData = WorkflowDataPart['data']

export function WorkflowChat() {
  const { messages, sendMessage } = useChat({
    transport: new DefaultChatTransport({
      api: 'http://localhost:4111/workflow/activitiesWorkflow',
      prepareSendMessagesRequest: ({ messages }) => ({
        body: { inputData: { location: messages[messages.length - 1]?.parts[0]?.text } },
      }),
    }),
  })

  return (
    <div>
      {messages.map(message =>
        message.parts.map((part, index) => {
          if (part.type !== 'data-workflow') return null
          const data = part.data as WorkflowData
          return (
            <div key={`${message.id}-${index}`}>
              <h3>{data.name}: {data.status}</h3>
              {Object.values(data.steps).map(step => (
                <p key={step.name}>{step.name}: {step.status}</p>
              ))}
            </div>
          )
        }),
      )}
      <button onClick={() => sendMessage({ text: 'Lisbon' })}>Plan</button>
    </div>
  )
}
```

Read `data-workflow-step` parts (`WorkflowStepDataPart`) when you need the full output of the step that just changed.
