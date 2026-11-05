# Framework integration API reference

Distilled from `https://mastra.ai/reference/ai-sdk/handle-chat-stream.md`, `https://mastra.ai/reference/ai-sdk/chat-route.md`, `https://mastra.ai/reference/ai-sdk/to-ai-sdk-messages.md`, `https://mastra.ai/reference/server/next-adapter.md`, `https://mastra.ai/reference/server/tanstack-start-adapter.md`, and `https://mastra.ai/reference/server/nestjs-adapter.md`. Full option tables live in `mastra-agentic-ui` and `mastra-server`.

## Contents

- In-app route helpers (shape A)
- Mastra server chat route (shape C)
- Adapter mount functions (shape B)
- Memory recall for history

---

## In-app route helpers (shape A)

### `handleChatStream(options)`

Import: `import { handleChatStream } from '@mastra/ai-sdk'`

| Option | Notes |
|---|---|
| `mastra` | Your Mastra instance. |
| `agentId` | Agent ID to run. |
| `version` | `'v5'` (default), `'v6'`, `'v7'`. Match the installed `ai` package. |
| `params` | Request body: `messages`, `memory`, `requestContext`, `runId`, `resumeData`, `providerOptions`. |
| `defaultOptions` | Agent execution defaults merged under `params`. |
| `onError` | `(error) => string` sent to the client. |

Returns a `ReadableStream`. Wrap it: `return createUIMessageStreamResponse({ stream })` (from `ai`).

### Message converters

Import from `@mastra/ai-sdk/ui`:

| Function | Use |
|---|---|
| `toAISdkMessages(messages, { version })` | Version-aware conversion (`v5` default, `v6`, `v7`). |
| `toAISdkV5Messages(messages)` | AI SDK v5 `UIMessage[]`. |
| `toAISdkV4Messages(messages)` | AI SDK v4 messages. |

---

## Mastra server chat route (shape C)

Import: `import { chatRoute } from '@mastra/ai-sdk'`

```typescript
chatRoute({ path: '/chat/:agentId' }) // dynamic agent
chatRoute({ path: '/chat', agent: 'weatherAgent' }) // fixed agent
```

Options: `path` (default `/chat/:agentId`), `agent`, `version`, `defaultOptions`, `sendReasoning`, `sendSources`, `heartbeatMs`. Add the result to `server.apiRoutes`. Browser apps on another origin also need `server.cors`.

---

## Adapter mount functions (shape B)

| Package | Function | Returns |
|---|---|---|
| `@mastra/next` | `createNextRouteHandler({ mastra, tools?, prefix? })` | `{ GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD }` with `(request: Request) => Response` |
| `@mastra/tanstack-start` | `createStartRouteHandler({ mastra, tools?, prefix? })` | Same keys, `(context: { request, params }) => Response` |
| `@mastra/express`, `@mastra/hono` | `new MastraServer({ app, mastra, prefix?, ... })` then `await server.init()` | |
| `@mastra/nestjs` | `MastraModule.register({ mastra, prefix?, ... })` or `registerAsync(...)` | Nest module; `MASTRA` token and `MastraService` |

`prefix` defaults to `/api` and must equal the mount path for Next.js and TanStack Start. Next.js and TanStack Start initialize lazily on the first request, so they work in serverless runtimes. Body size defaults to 4.5 MB (`server.bodySizeLimit`).

---

## Memory recall for history

```typescript
const memory = await mastra.getAgentById('weather-agent').getMemory()
const response = await memory?.recall({ threadId, resourceId })
// response?.messages -> pass to toAISdkMessages() or toAISdkV5Messages()
```

`recall()` throws when no thread exists yet. Wrap it in `try/catch` and return an empty list.
