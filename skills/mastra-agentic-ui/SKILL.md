---
name: mastra-agentic-ui
description: "Build chat and generative UIs on top of Mastra agents and workflows with @mastra/ai-sdk and AI SDK UI (useChat, useCompletion), assistant-ui, CopilotKit, and OpenUI. Covers chatRoute, workflowRoute, networkRoute, handleChatStream, handleWorkflowStream, toAISdkStream, message converters, tool part rendering, custom data parts from writer.custom, browser-side client tools, suspended tool resume, memory-aware requests, and SSE heartbeats. Use this skill whenever the user wants a chat interface, streaming UI, tool cards, workflow progress UI, or wants to connect a React, Vue, Svelte, or Angular frontend to a Mastra agent. Triggers on @mastra/ai-sdk, chatRoute, handleChatStream, toAISdkStream, toAISdkMessages, toAISdkV5Messages, withSseHeartbeat, withMastra, useChat, DefaultChatTransport, prepareSendMessagesRequest, addToolOutput, tool-weatherTool part, data-workflow, assistant-ui, useChatRuntime, CopilotKit, registerCopilotKit, @ag-ui/mastra, OpenUI, AgentInterface."
license: Apache-2.0
metadata:
  category: server-and-frontend
  catalog_summary: "AI SDK UI routes and converters, useChat, tool and workflow rendering, assistant-ui, CopilotKit, OpenUI"
  display_order: 4
  docs: https://mastra.ai/integrations/agentic-ui/ai-sdk-ui
---

# Mastra Agentic UI

Stream Mastra agents and workflows into a frontend chat or generative UI, using AI SDK UI or an AG-UI based library.

---

## When to use

- Building a chat page with `useChat()` against a Mastra agent
- Rendering tool calls, workflow steps, or progress events as components
- Running tools in the browser and feeding results back to the agent
- Resuming a suspended tool or approving a tool call from the UI
- Converting stored memory messages into `UIMessage[]` for initial history
- Using assistant-ui, CopilotKit, or OpenUI as the frontend
- Wrapping an existing AI SDK model with Mastra memory or processors (`withMastra`)

## When NOT to use

- Framework scaffolding and where to put the route file (use `mastra-framework-integration`)
- Calling agents from a frontend without AI SDK UI (use `mastra-client-sdk`)
- Stream chunk types on the server (`fullStream`, `textStream`) (use `mastra-streaming`)
- Tool definitions and `writer` on the tool side (use `mastra-tools`)
- Approval and suspension design (use `mastra-agent-approval-hitl` and `mastra-workflow-suspend-resume`)
- Server middleware, CORS, custom route plumbing (use `mastra-server`)
- Protecting the chat route (use `mastra-auth`)

---

## Required inputs

- The UI library: AI SDK UI (`@ai-sdk/react`, `@ai-sdk/vue`, `@ai-sdk/svelte`, `@ai-sdk/angular`), assistant-ui, CopilotKit, or OpenUI
- The installed `ai` major version (v5, v6, or v7)
- Where the route runs: Mastra server (`chatRoute`) or your framework (`handleChatStream`)
- The agent or workflow ID, and whether memory is on
- Which tool outputs or events need custom rendering

---

## The framework: Mastra stream in, AI SDK parts out

`@mastra/ai-sdk` converts Mastra streams into AI SDK UI message streams. Pick the helper by where the route lives:

| Target | On the Mastra server | In your own route |
|---|---|---|
| Agent chat | `chatRoute()` | `handleChatStream()` |
| Workflow | `workflowRoute()` | `handleWorkflowStream()` |
| Agent network (deprecated) | `networkRoute()` | `handleNetworkStream()` |
| Anything custom | `registerApiRoute()` + `toAISdkStream()` | `toAISdkStream()` |

```typescript
// Mastra server: src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { chatRoute } from '@mastra/ai-sdk'

export const mastra = new Mastra({
  server: {
    apiRoutes: [chatRoute({ path: '/chat/:agentId', version: 'v7' })],
  },
})
```

```tsx
// Frontend
import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport } from 'ai'

export function Chat() {
  const { messages, sendMessage } = useChat({
    transport: new DefaultChatTransport({ api: 'http://localhost:4111/chat/weatherAgent' }),
  })
  return (
    <div>
      {messages.map(m => (
        <div key={m.id}>
          {m.parts.map((part, i) => (part.type === 'text' ? <p key={i}>{part.text}</p> : null))}
        </div>
      ))}
      <button onClick={() => sendMessage({ text: 'Weather in Paris?' })}>Ask</button>
    </div>
  )
}
```

### Parts you will render

| Part type | Source | Notes |
|---|---|---|
| `text` | Agent text | Plain text. |
| `tool-{toolKey}` | Tool calls | States `input-streaming`, `input-available`, `output-available`, `output-error`. `toolKey` is the key in the agent's `tools` object. |
| `data-workflow`, `data-workflow-step` | Workflow routes | Snapshot and per-step delta. |
| `data-tool-agent`, `data-tool-agent-step` | Subagents | Disable with `includeSubAgentMetadata: false`. |
| `data-tool-call-suspended`, `data-tool-call-approval` | Suspended or approval tools | Carry `runId` and `toolCallId`. |
| `data-structured-output` | `structuredOutput` | Final object only. |
| `data-{custom}` | `await context.writer.custom({ type: 'data-...', data })` in a tool | Must start with `data-`. |

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/ai-sdk` exists, read its `dist/docs/` and types. Otherwise fetch `https://mastra.ai/integrations/agentic-ui/ai-sdk-ui.md` and `https://mastra.ai/reference/ai-sdk/chat-route.md`. Trust these over memory.
2. **Install** `@mastra/ai-sdk`, `ai`, and the UI binding for your framework.
3. **Match versions.** Pass `version: 'v6'` or `'v7'` to routes, handlers, `toAISdkStream()`, and `toAISdkMessages()` when the installed `ai` is not v5.
4. **Add the route.** `chatRoute()` in `server.apiRoutes`, or `handleChatStream()` wrapped in `createUIMessageStreamResponse()`.
5. **Wire memory.** In `prepareSendMessagesRequest`, send only the last message plus `memory: { thread, resource }`. Load history with `toAISdkMessages()`.
6. **Render parts.** Switch on `part.type` and the tool `state`. Give tools an `outputSchema` so the UI knows the output shape.
7. **Add client tools or resume flows** if needed (deep dive below).
8. **Keep connections alive** behind proxies with `heartbeatMs` on routes or `withSseHeartbeat()`.
9. **Test** the stream in the browser and check the network tab for SSE chunks.

---

## Deep dive: client tools and resume from `useChat()`

A tool without `execute` runs in the browser. The run ends at that step with a `tool-{toolKey}` part in `input-available`. Run the tool, add its output, and resend:

```tsx
import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport, lastAssistantMessageIsCompleteWithToolCalls } from 'ai'

const { messages, sendMessage, addToolOutput } = useChat({
  transport: new DefaultChatTransport({ api: 'http://localhost:4111/chat' }),
  sendAutomaticallyWhen: lastAssistantMessageIsCompleteWithToolCalls,
  async onToolCall({ toolCall }) {
    if (toolCall.toolName === 'addToCart') {
      const input = toolCall.input as { productId: string }
      const cart = await addToCartInBrowser(input.productId)
      // Don't await addToolOutput inside onToolCall
      addToolOutput({ tool: 'addToCart', toolCallId: toolCall.toolCallId, output: cart })
    }
  },
})
```

Subagents can't run client tools. Define them on the agent the route talks to.

To resume a suspended tool, send `runId` and `resumeData` in the body (from the latest `data-tool-call-suspended` part). `chatRoute()` and `handleChatStream()` then call `agent.resumeStream()`. See `references/examples.md`.

---

## Failure patterns

- **Type errors on `UIMessage` or stream parts.** The helper emits v5 by default. Pass `version` matching the installed `ai`.
- **Duplicate or out-of-order messages with memory.** The client sends the full history. Send only the last message with `memory.thread` and `memory.resource`.
- **Duplicated assistant message with `toAISdkStream()`.** Pass `originalMessages: messages` to `createUIMessageStream()`.
- **`WritableStream is locked`.** A `writer.custom()` call was not awaited.
- **Custom event never reaches the UI.** Its `type` does not start with `data-`.
- **Tool part never matches.** The UI checks `tool-get-weather` (the tool `id`) instead of `tool-weatherTool` (the `tools` object key).
- **Generation stops when the tab closes.** `chatRoute()` forwards the request abort signal. Build a custom route with `consumeStream()` to keep going (see `mastra-server`).
- **Editing or regenerating a message does not change stored history.** With memory, storage is the source of truth. Update stored messages, then send a new message.
- **Stream drops during long tool calls.** A proxy closed the idle connection. Set `heartbeatMs` or wrap with `withSseHeartbeat()`.
- **CopilotKit returns 500 after `mastra build`.** Add `@copilotkit/runtime` to `bundler.externals`.
- **New code built on `networkRoute()`.** Agent networks are deprecated. Use a supervisor agent with `chatRoute()` (see `mastra-multi-agent`).

---

## Output format

A finished agentic UI contains:

- The route: `chatRoute()`/`workflowRoute()` in `src/mastra/index.ts`, or a framework route with a `handle*Stream()` helper
- The chat component with part rendering for text, each tool, and custom data parts
- Memory wiring (thread and resource from app state) and a history loader
- Any client tools and resume handling, with the matching server-side tool definitions
- A manual test note covering a tool call, an error state, and a reload with history

---

## Reference files

- [`references/api.md`](references/api.md) - Every `@mastra/ai-sdk` export with options and defaults.
- [`references/libraries.md`](references/libraries.md) - assistant-ui, CopilotKit, and OpenUI setup and options.
- [`references/examples.md`](references/examples.md) - Tool cards, custom progress events, request data to request context, suspended tool resume, workflow streaming.
- [`references/checklist.md`](references/checklist.md) - Agentic UI checklist.

**Live docs**

- https://mastra.ai/integrations/agentic-ui/ai-sdk-ui
- https://mastra.ai/integrations/agentic-ui/assistant-ui
- https://mastra.ai/integrations/agentic-ui/copilotkit
- https://mastra.ai/integrations/agentic-ui/openui
- https://mastra.ai/reference/ai-sdk/chat-route
- https://mastra.ai/reference/ai-sdk/handle-chat-stream
- https://mastra.ai/reference/ai-sdk/to-ai-sdk-stream
- https://mastra.ai/reference/ai-sdk/to-ai-sdk-messages
