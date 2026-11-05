# UI libraries: assistant-ui, CopilotKit, OpenUI

Distilled from `https://mastra.ai/integrations/agentic-ui/assistant-ui.md`, `https://mastra.ai/integrations/agentic-ui/copilotkit.md`, and `https://mastra.ai/integrations/agentic-ui/openui.md`. These libraries ship their own APIs. Check their docs for component details.

## Contents

- Comparison
- assistant-ui
- CopilotKit
- OpenUI

---

## Comparison

| Library | Protocol | Server side | Client side | Packages |
|---|---|---|---|---|
| AI SDK UI | AI SDK UI message stream | `chatRoute()` or `handleChatStream()` | `useChat()` | `@mastra/ai-sdk`, `ai`, `@ai-sdk/react` (or vue, svelte, angular) |
| assistant-ui | AI SDK UI message stream | `chatRoute({ path: '/chat/:agentId' })` | `useChatRuntime({ transport: new AssistantChatTransport({ api }) })` | `@mastra/ai-sdk`; `npx assistant-ui@latest create` |
| CopilotKit | AG-UI | `registerCopilotKit({ path, resourceId })` in `apiRoutes` | `<CopilotKit runtimeUrl agent>` plus `CopilotChat` or `CopilotSidebar` | `@ag-ui/mastra @mastra/client-js @mastra/core @ag-ui/core @ag-ui/client @copilotkit/runtime`; UI: `@copilotkit/react-ui @copilotkit/react-core` |
| OpenUI | AG-UI | `new MastraAgent({ agent, resourceId })` run in a Next.js route as SSE | `<AgentInterface llm={fetchLLM({ url, streamAdapter: agUIAdapter() })} componentLibrary>` | `@mastra/core @ag-ui/mastra @ag-ui/core zod`; `@openuidev/react-ui` |

---

## assistant-ui

1. Add `chatRoute({ path: '/chat/:agentId' })` to the Mastra server `apiRoutes` and run it on port 4111.
2. Create the frontend with `npx assistant-ui@latest create`.
3. Point the runtime at the Mastra route:

```tsx
'use client'

export const Assistant = () => {
  const runtime = useChatRuntime({
    transport: new AssistantChatTransport({
      api: 'http://localhost:4111/chat/weatherAgent',
    }),
  })
  // Rest of the component...
}
```

For Mastra inside Next.js API routes instead of a separate server, follow assistant-ui's own full-stack Mastra guide.

---

## CopilotKit

Server (`src/mastra/index.ts`):

```typescript
import { Mastra } from '@mastra/core/mastra'
import { registerCopilotKit } from '@ag-ui/mastra/copilotkit'

export const mastra = new Mastra({
  server: {
    cors: {
      origin: '*', // restrict to your frontend in production
      allowMethods: ['*'],
      allowHeaders: ['*'],
    },
    apiRoutes: [
      registerCopilotKit({
        path: '/copilotkit',
        resourceId: 'weatherAgent',
      }),
    ],
  },
  bundler: {
    externals: ['@copilotkit/runtime'], // required for mastra build
  },
})
```

Client:

```tsx
import { CopilotChat } from '@copilotkit/react-ui'
import { CopilotKit } from '@copilotkit/react-core'
import '@copilotkit/react-ui/styles.css'

export default function Home() {
  return (
    <CopilotKit runtimeUrl="http://localhost:4111/copilotkit" agent="weatherAgent">
      <CopilotChat labels={{ title: 'Weather Agent', initial: 'Ask me about the weather.' }} />
    </CopilotKit>
  )
}
```

The `agent` prop must match a key in the Mastra `agents` map. The endpoint exposes every registered agent.

`registerCopilotKit()` options:

| Option | Use |
|---|---|
| `path` | Route path, such as `/copilotkit`. |
| `resourceId` | Scope Mastra memory for conversations. |
| `cors` | Per-route CORS on top of `server.cors`. |
| `setContext` | Populate request context before agents run (auth, per-user resource IDs). |
| `agents` | Pre-built AG-UI agents instead of the Mastra registry. |
| `tracingOptions` | Forward Mastra tracing options. |

Other options pass through to the CopilotKit runtime (for example `mcpApps`).

Client hooks used in the guide:

| Hook | Import | Purpose |
|---|---|---|
| `useRenderTool({ name, parameters, render })` | `@copilotkit/react-core/v2` | Render a Mastra tool call as a component. |
| `useComponent({ name, render, parameters })` | `@copilotkit/react-core/v2` | Let the agent emit a component. |
| `useAgent()` | `@copilotkit/react-core/v2` | Read shared agent state. |
| `useFrontendTool({ name, description, parameters, handler })` | `@copilotkit/react-core` | Browser-side tool. |
| `useHumanInTheLoop({ name, parameters, render })` | `@copilotkit/react-core` | Pause for the user and `respond`. |

CopilotKit channels (`@copilotkit/channels`, `@copilotkit/channels/slack`) deploy the same AG-UI agent to Slack and other platforms.

---

## OpenUI

Run in a Next.js route (`src/app/api/chat/route.ts`):

```typescript
import { MastraAgent } from '@ag-ui/mastra'
import { Agent } from '@mastra/core/agent'
import type { Message } from '@ag-ui/core'
import { NextRequest } from 'next/server'
import { readFileSync } from 'fs'
import { join } from 'path'

const systemPrompt = readFileSync(join(process.cwd(), 'src/generated/system-prompt.txt'), 'utf-8')

const agent = new MastraAgent({
  agent: new Agent({
    id: 'openui-agent',
    name: 'OpenUI Agent',
    instructions: `You are a helpful assistant. Use tools when relevant.\n\n${systemPrompt}`,
    model: 'openai/gpt-6.1-sol',
  }),
  resourceId: 'chat-user',
})

export async function POST(req: NextRequest) {
  const { messages, threadId }: { messages: Message[]; threadId: string } = await req.json()
  const encoder = new TextEncoder()

  const stream = new ReadableStream({
    start(controller) {
      const subscription = agent
        .run({ messages, threadId, runId: crypto.randomUUID(), tools: [], context: [] })
        .subscribe({
          next: event => controller.enqueue(encoder.encode(`data: ${JSON.stringify(event)}\n\n`)),
          complete: () => {
            controller.enqueue(encoder.encode('data: [DONE]\n\n'))
            controller.close()
          },
          error: error => {
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ error: error.message })}\n\n`))
            controller.close()
          },
        })
      req.signal.addEventListener('abort', () => subscription.unsubscribe())
    },
  })

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      Connection: 'keep-alive',
    },
  })
}
```

Client (`src/app/page.tsx`):

```tsx
'use client'

import '@openuidev/react-ui/components.css'
import { AgentInterface, agUIAdapter, fetchLLM } from '@openuidev/react-ui'
import { openuiChatLibrary } from '@openuidev/react-ui/genui-lib'

const llm = fetchLLM({ url: '/api/chat', streamAdapter: agUIAdapter() })

export default function Page() {
  return <AgentInterface llm={llm} componentLibrary={openuiChatLibrary} />
}
```

- Scaffold with `npx @openuidev/cli@latest create --name openui-mastra-chat`.
- Libraries: `openuiChatLibrary` or `openuiDashboardLibrary`, or your own in `src/library.ts`.
- Regenerate the prompt after library changes: `npx @openuidev/cli generate src/library.ts --out src/generated/system-prompt.txt`.
- Generate a fresh `runId` per request. Persist `threadId` on the client.
- The OpenUI guide passes the model as `{ id: 'openai/gpt-6.1-sol', apiKey: process.env.OPENAI_API_KEY }`. A plain router string works when the env var is set.
