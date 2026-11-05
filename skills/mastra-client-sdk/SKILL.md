---
name: mastra-client-sdk
description: "Call a running Mastra server from a browser, a frontend framework, or another backend with MastraClient from @mastra/client-js: agents (generate, stream, processDataStream, client tools, tool approval), workflows (createRun, startAsync, stream, resume), memory threads and messages, tools, vectors, logs, traces and feedback, datasets and experiments, the OpenAI-compatible Responses and Conversations APIs, and agent controller sessions. Use this skill whenever the user wants to talk to Mastra over HTTP instead of importing the mastra instance, pass auth headers or cookies, cancel requests, retry, or render streamed chunks in a UI. Triggers on MastraClient, @mastra/client-js, mastraClient.getAgent, getWorkflow, createRun, startAsync, processDataStream, clientTools, approveToolCall, listMemoryThreads, getMemoryThread, client.responses.create, client.conversations, getAgentController, credentials include, MastraClientError. Also triggers when a frontend gets 401 or CORS errors calling Mastra."
license: Apache-2.0
metadata:
  category: server-and-frontend
  catalog_summary: "MastraClient for agents, workflows, memory, tools, vectors, traces, datasets, Responses API, agent controller"
  display_order: 2
  docs: https://mastra.ai/docs/server/mastra-client
---

# Mastra Client SDK

Call agents, workflows, memory, and other resources on a Mastra server over HTTP with the type-safe `MastraClient`.

---

## When to use

- A frontend (React, Vue, Svelte, Angular, Electron) calls a separate Mastra server
- A backend service, serverless function, or script calls a deployed Mastra server
- Streaming agent output to a UI with `processDataStream()`
- Running browser-side tools (`clientTools`) that the agent can call
- Starting, streaming, resuming, or polling workflow runs remotely
- Managing memory threads and messages, or reading traces and logs from another process
- Using Mastra agents through the OpenAI-compatible Responses API

## When NOT to use

- Code that runs in the same process as the `mastra` instance (call `mastra.getAgentById()` directly, see `mastra-agents`)
- `useChat()` and AI SDK UI rendering (use `mastra-agentic-ui`)
- Defining server routes, middleware, or CORS (use `mastra-server`)
- Choosing and configuring an auth provider (use `mastra-auth`)
- Shell calls to the API (use `mastra-cli-api`)
- Workflow suspend and resume design (use `mastra-workflow-suspend-resume`)
- Tool approval design on the agent side (use `mastra-agent-approval-hitl`)

---

## Required inputs

- The server URL (`MASTRA_API_URL`, default `http://localhost:4111`) and any custom API prefix
- How the caller authenticates: bearer token header, session cookie, or none
- Which resources it calls: agent IDs, workflow IDs, thread and resource IDs
- Whether output is streamed to a UI or awaited as a whole
- Whether the client runs in a browser (CORS, cookies) or on a server

---

## The framework: one client, resource handles

`MastraClient` wraps the server's REST API. Create one instance per app, then get lightweight handles for each resource. Handles do no network work until you call a method.

```typescript
// lib/mastra-client.ts
import { MastraClient } from '@mastra/client-js'

export const mastraClient = new MastraClient({
  baseUrl: process.env.MASTRA_API_URL || 'http://localhost:4111',
})
```

```typescript
import { mastraClient } from './lib/mastra-client'

const agent = mastraClient.getAgent('weather-agent')

const response = await agent.generate('What is the weather in London?', {
  memory: { thread: 'thread-1', resource: 'user-123' },
})
console.log(response.text)

const stream = await agent.stream('Tell me a story')
await stream.processDataStream({
  onChunk: async chunk => {
    if (chunk.type === 'text-delta') console.log(chunk.payload.text)
  },
})
```

| Handle | Get it with | Main methods |
|---|---|---|
| Agent | `getAgent(id)` | `details`, `generate`, `stream`, `sendMessage`, `subscribeToThread`, `approveToolCall`, `declineToolCall`, `resumeStream`, `listSuspendedRuns` |
| Workflow | `getWorkflow(id)` | `details`, `createRun` then `start`, `startAsync`, `stream`, `resume`, `resumeAsync`, `cancel`; `runById` |
| Memory thread | `getMemoryThread({ threadId, agentId })` | `get`, `update`, `delete`, `clone`, `listMessages`, `deleteMessages` |
| Tool | `getTool(id)` | `details`, `execute({ args })` |
| Vector | `getVector(name)` | `createIndex`, `upsert`, `query`, `getIndexes`, `delete` |
| Responses | `client.responses` | `create`, `stream`, `retrieve`, `delete` |
| Agent controller | `getAgentController(key).session(id)` | `create`, `subscribe`, `sendMessage`, `approveTool`, `state` |

Top-level methods cover listing (`listAgents`, `listWorkflows`, `listTools`), memory (`listMemoryThreads`, `createMemoryThread`, `saveMessageToMemory`), logs, traces, scores, feedback, and datasets.

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/client-js` exists, read its `dist/docs/` and type definitions. Otherwise fetch `https://mastra.ai/docs/server/mastra-client.md` and `https://mastra.ai/reference/client-js/agents.md`. Trust these over memory.
2. **Install** `@mastra/client-js` in the calling app (not necessarily the Mastra server project).
3. **Create one client** with `baseUrl` from env. Add `apiPrefix` only if the server changed it.
4. **Add auth.** Pass `headers: { Authorization: 'Bearer ...' }` for tokens, or `credentials: 'include'` for session cookies across origins (see `mastra-auth`).
5. **Call resources by ID.** Use the agent `id` or registration key the server knows. Confirm with `await mastraClient.listAgents()`.
6. **Choose generate or stream.** Use `stream()` plus `processDataStream()` for UIs. Use `generate()` for jobs and scripts.
7. **Pass request context** with `RequestContext` from `@mastra/client-js` or a plain object.
8. **Handle errors and cancellation.** Wrap calls in `try/catch`. Pass `abortSignal` per call, or cancel the response body reader.
9. **Test** against `mastra dev` on port 4111, then against the deployed URL.

---

## Deep dive: client tools and approvals

Client tools run in the browser. Define them with `createTool` from `@mastra/client-js` and pass them per call.

```typescript
import { createTool } from '@mastra/client-js'
import { z } from 'zod'

const colorChangeTool = createTool({
  id: 'changeColor',
  description: 'Changes the background color',
  inputSchema: z.object({ color: z.string() }),
  execute: async inputData => {
    document.body.style.backgroundColor = inputData.color
    return { success: true }
  },
})

const response = await mastraClient
  .getAgent('color-agent')
  .generate('Change the background to blue', { clientTools: { colorChangeTool } })
```

For tools that need approval, list waiting runs with `agent.listSuspendedRuns({ threadId, resourceId })`. Resume a streamed run with `approveToolCall({ runId, toolCallId })` or `declineToolCall({ runId, toolCallId, reason })`. Use `approveToolCallGenerate()` after a `generate()` call that finished with `finishReason === 'suspended'`.

---

## Failure patterns

- **`401` from the browser after login.** Cookies are not sent cross-origin. Set `credentials: 'include'` and allow credentials with a concrete origin on the server.
- **CORS error before the request reaches Mastra.** The server's `cors.origin` does not include the frontend origin, or uses `'*'` with credentials.
- **Wrong `baseUrl` path.** `baseUrl` is the server origin (`http://localhost:4111`), not `.../api`. The client adds the prefix.
- **Agent not found.** The ID does not match the server registry. Check `listAgents()`.
- **Importing `RequestContext` from `@mastra/core` in a frontend.** Import it from `@mastra/client-js`, or pass a plain object.
- **Client tool never runs.** It was defined with `@mastra/core/tools` or not passed in `clientTools` on that call.
- **Stream looks empty.** `processDataStream()` was not awaited or no `onChunk` handler checks `chunk.type`.
- **Stopping the UI does not stop a durable run.** Cancelling the body only disconnects. Call `agent.abortRun(runId)` or pass a per-call `abortSignal`.
- **Sending full chat history with memory enabled.** Send only the new message plus `memory.thread` and `memory.resource`.
- **`listWorkflowRunCounts()` returns 404.** The server predates the endpoint. Handle the error.

---

## Output format

A finished client integration contains:

- `lib/mastra-client.ts` (or similar) exporting one configured `MastraClient`
- `MASTRA_API_URL` and any token variable in `.env.example`
- Call sites that pass `memory`, `requestContext`, and `abortSignal` where relevant
- Error handling around every call
- A manual or automated check against a running server

---

## Reference files

- [`references/api.md`](references/api.md) - Constructor options and every resource method with parameters.
- [`references/examples.md`](references/examples.md) - Streaming chat with memory, workflow run with resume, authenticated server-side call, Responses API.
- [`references/checklist.md`](references/checklist.md) - Client integration checklist.

**Live docs**

- https://mastra.ai/docs/server/mastra-client
- https://mastra.ai/reference/client-js/mastra-client
- https://mastra.ai/reference/client-js/agents
- https://mastra.ai/reference/client-js/workflows
- https://mastra.ai/reference/client-js/memory
- https://mastra.ai/reference/client-js/responses
- https://mastra.ai/reference/client-js/agent-controller
- https://mastra.ai/reference/client-js/error-handling
