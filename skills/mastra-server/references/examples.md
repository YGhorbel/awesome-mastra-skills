# Server examples

All examples follow the current docs. Verify imports and option names against the installed version before copying.

## Contents

1. Validated custom routes with OpenAPI output
2. Tenant middleware feeding request context
3. Hono adapter with manual initialization and auth on raw routes
4. A streaming route that survives client disconnects

---

## 1. Validated custom routes with OpenAPI output

```typescript
// src/mastra/routes/items.ts
import { createRoute } from '@mastra/server/server-adapter'
import { z } from 'zod'

export const createItemRoute = createRoute({
  method: 'POST',
  path: '/items',
  responseType: 'json',
  bodySchema: z.object({
    name: z.string().min(1),
  }),
  responseSchema: z.object({
    id: z.string(),
    name: z.string(),
  }),
  handler: async ({ name }) => ({
    id: crypto.randomUUID(),
    name,
  }),
})

export const listItemsRoute = createRoute({
  method: 'GET',
  path: '/items',
  responseType: 'json',
  queryParamSchema: z.object({
    page: z.coerce.number().default(0),
    limit: z.coerce.number().default(50),
  }),
  handler: async ({ page, limit }) => ({ items: [], page, limit }),
})
```

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { createItemRoute, listItemsRoute } from './routes/items'

export const mastra = new Mastra({
  server: {
    build: {
      openAPIDocs: true,
      swaggerUI: true,
    },
    onValidationError: (error, context) => ({
      status: 422,
      body: {
        ok: false,
        errors: error.issues.map(i => ({ path: i.path.join('.'), message: i.message })),
        source: context,
      },
    }),
    apiRoutes: [createItemRoute, listItemsRoute],
  },
})
```

```bash
curl -X POST http://localhost:4111/items -H "Content-Type: application/json" -d '{"name":""}'
# 422 with the custom error body
```

---

## 2. Tenant middleware feeding request context

The middleware sets values that the agent validates with `requestContextSchema`.

```typescript
// src/mastra/agents/weather-agent.ts
import { Agent } from '@mastra/core/agent'
import { z } from 'zod'

export const weatherAgent = new Agent({
  id: 'weather-agent',
  name: 'Weather Agent',
  requestContextSchema: z.object({
    'temperature-unit': z.enum(['celsius', 'fahrenheit']),
  }),
  instructions: ({ requestContext }) =>
    `Answer weather questions. Report temperatures in ${requestContext.get('temperature-unit')}.`,
  model: 'openai/gpt-6.1-sol',
})
```

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { weatherAgent } from './agents/weather-agent'

const notFound = async () => new Response('Not Found', { status: 404 })

export const mastra = new Mastra({
  agents: { weatherAgent },
  server: {
    middleware: [
      // Hide route groups you don't use
      { path: '/api/logs/*', handler: notFound },
      // Derive per-request values from headers
      async (c, next) => {
        const country = c.req.header('CF-IPCountry')
        c.get('requestContext').set('temperature-unit', country === 'US' ? 'fahrenheit' : 'celsius')
        await next()
      },
      // Request timing
      async (c, next) => {
        const start = Date.now()
        await next()
        console.log(`${c.req.method} ${c.req.url} - ${Date.now() - start}ms`)
      },
    ],
  },
})
```

This works with `mastra dev`, `mastra build`, `@mastra/hono`, `@mastra/next`, and `@mastra/tanstack-start`. Other adapters need framework middleware.

---

## 3. Hono adapter with manual initialization and auth on raw routes

```typescript
// src/server.ts
import { Hono } from 'hono'
import { serve } from '@hono/node-server'
import { createAuthMiddleware, HonoBindings, HonoVariables, MastraServer } from '@mastra/hono'
import { mastra } from './mastra'

const app = new Hono<{ Bindings: HonoBindings; Variables: HonoVariables }>()

// Runs before Mastra context exists
app.get('/early-health', c => c.json({ status: 'ok' }))

const server = new MastraServer({
  app,
  mastra,
  prefix: '/api/v2',
  openapiPath: '/openapi.json',
  customRouteAuthConfig: new Map([['GET:/api/v2/agents', false]]),
})
await server.init()

// After init: Mastra context and auth helpers are available
app.get('/custom/protected', createAuthMiddleware({ mastra }), c => {
  const user = c.get('requestContext').get('user')
  return c.json({ user })
})

serve({ fetch: app.fetch, port: 4111 }, async () => {
  await mastra.startWorkers()
})

process.on('SIGTERM', async () => {
  await mastra.shutdown()
  process.exit(0)
})
```

---

## 4. A streaming route that survives client disconnects

`chatRoute()` cancels generation when the browser disconnects. This route keeps generating and persists the final answer through memory.

```typescript
import {
  createUIMessageStream,
  createUIMessageStreamResponse,
  InferUIMessageChunk,
  UIMessage,
} from 'ai'
import { toAISdkStream } from '@mastra/ai-sdk'
import { Mastra } from '@mastra/core'
import { registerApiRoute } from '@mastra/core/server'

export const mastra = new Mastra({
  server: {
    apiRoutes: [
      registerApiRoute('/chat/persist/:agentId', {
        method: 'POST',
        handler: async c => {
          const { messages, memory } = await c.req.json()
          const mastra = c.get('mastra')
          const agent = mastra.getAgent(c.req.param('agentId'))

          // No abortSignal: keep running after the client leaves
          const stream = await agent.stream(messages, { memory })

          void stream.consumeStream().catch(error => {
            mastra.getLogger()?.error('Background stream consumption failed', { error })
          })

          const uiStream = createUIMessageStream({
            originalMessages: messages,
            execute: async ({ writer }) => {
              for await (const part of toAISdkStream(stream, { from: 'agent' })) {
                writer.write(part as InferUIMessageChunk<UIMessage>)
              }
            },
          })

          return createUIMessageStreamResponse({ stream: uiStream })
        },
      }),
    ],
  },
})
```

To cancel on disconnect instead, pass `abortSignal: c.req.raw.signal` to `agent.stream()`.
