# Server adapters

Distilled from `https://mastra.ai/docs/server/server-adapters.md`, the per-adapter reference pages under `https://mastra.ai/reference/server/`, and `https://mastra.ai/docs/server/custom-adapters.md`.

Adapters mount Mastra's routes on your own HTTP framework. They use the `mastra` instance you pass and do not run file-based agent discovery, so register agents in code. To use Studio with an adapter, run `mastra studio`.

## Contents

- Adapter table
- Shared behavior
- Per-adapter notes
- Custom adapters

---

## Adapter table

| Framework | Install | Mount | Context access | `server.middleware` |
|---|---|---|---|---|
| Express | `@mastra/express` | `new MastraServer({ app, mastra })` then `await server.init()` | `res.locals.mastra`, `res.locals.requestContext` | Warns, not run |
| Hono | `@mastra/hono hono` | `new Hono<{ Bindings: HonoBindings; Variables: HonoVariables }>()` then `MastraServer` | `c.get('mastra')`, `c.get('requestContext')` | Runs |
| Fastify | `@mastra/fastify` | `MastraServer` on `Fastify()` | `request.mastra`, `request.requestContext` | Warns, not run |
| Koa | `@mastra/koa` | `app.use(bodyParser())` first, then `MastraServer` | `ctx.state.mastra`, `ctx.state.requestContext` | Warns, not run |
| Elysia | `@mastra/elysia elysia` | `MastraServer` on `new Elysia()` | Elysia context | Warns, not run |
| NestJS | `@mastra/nestjs` | `MastraModule.register({ mastra })` in a module | `@Inject(MASTRA)` or `MastraService` | Warns, not run |
| Next.js | `@mastra/next hono` | `createNextRouteHandler({ mastra })` in a catch-all route | Hono context | Runs |
| TanStack Start | `@mastra/tanstack-start hono` | `createStartRouteHandler({ mastra })` in a splat route | Hono context | Runs |

Each `MastraServer` adapter exports `createAuthMiddleware({ mastra, requiresAuth? })` for raw framework routes that need Mastra auth.

---

## Shared behavior

- `init()` registers context, auth, user middleware, then routes. It does not start workers.
- Call `await mastra.startWorkers()` after the server listens. Without it, scheduled workflows, agent schedules, and event listeners never run.
- Call `await mastra.shutdown()` on `SIGTERM`. It drains in-flight workflow runs within `drainTimeout` (default 5 s).
- Routes added before `init()` have no Mastra context. Middleware added after `init()` never runs on Mastra routes.
- `prefix` changes `/api` (for example `/api/v2`). Custom framework routes are not prefixed.
- `customRouteAuthConfig: new Map([['GET:/api/health', false], ['ALL:/api/internal/*', true]])` overrides auth per route.
- `streamOptions: { redact: true }` is the default. Turn it off only for internal debugging.
- Adapters read `auth`, `bodySizeLimit`, `onError`, and `middleware` from `server` config. They ignore `port`, `host`, `cors`, `timeout`, and `apiRoutes` there (configure with the framework).
- MCP servers are exposed at `/api/mcp/:serverId/mcp`.

### Manual initialization

```typescript
const server = new MastraServer({ app, mastra })

app.use(loggingMiddleware) // before Mastra context
server.registerContextMiddleware()
app.use(customMiddleware) // has Mastra context
server.registerUserMiddleware()
await server.registerRoutes()
app.get('/health', handler) // after Mastra routes
```

---

## Per-adapter notes

### Express

```typescript
import express from 'express'
import { MastraServer } from '@mastra/express'
import { mastra } from './mastra'

const app = express()
app.use(express.json())
const server = new MastraServer({ app, mastra })
await server.init()
app.listen(4111)
```

`express.json()` is required. The abort signal is created from `res.on('close')` and fires only when the response did not finish.

### Hono

```typescript
import { Hono } from 'hono'
import { serve } from '@hono/node-server'
import { HonoBindings, HonoVariables, MastraServer } from '@mastra/hono'
import { mastra } from './mastra'

const app = new Hono<{ Bindings: HonoBindings; Variables: HonoVariables }>()
const server = new MastraServer({ app, mastra })
await server.init()

serve({ fetch: app.fetch, port: 4111 })
```

Hono context keys: `mastra`, `requestContext`, `abortSignal`, `registeredTools`, `taskStore`, `customRouteAuthConfig`, `user`.

### Fastify and Koa

Fastify reads `request.mastra`. Koa needs `koa-bodyparser` and reads `ctx.state.mastra`. Protect raw routes with `{ preHandler: createAuthMiddleware({ mastra }) }` (Fastify) or `app.use(createAuthMiddleware({ mastra }))` (Koa).

### Elysia

Install `elysia` with the adapter. `createAuthMiddleware()` forwards refreshed session headers. If you use it without `MastraServer`, register `applyAuthRefreshHeaders` yourself.

### NestJS

```typescript
import { Module } from '@nestjs/common'
import { MastraModule } from '@mastra/nestjs'
import { mastra } from './mastra'

@Module({ imports: [MastraModule.register({ mastra })] })
export class AppModule {}
```

- `MastraModule` registers a catch-all `@All('*')` controller. Import it last or mount under a prefix such as `/api/v1/mastra`.
- Module options add `rateLimitOptions` (on by default), `shutdownOptions`, `tracingOptions`, `contextOptions`, and `auth: { enabled, allowQueryApiKey }`.
- Use `MastraModule.registerAsync({ imports, useFactory, inject })` for config-driven setup.
- Start workers with `await app.get<Mastra>(MASTRA).startWorkers()` after `app.listen()`.
- Requires the Express platform (`@nestjs/platform-express`).

### Next.js

```typescript
// src/app/api/[...mastra]/route.ts
import { createNextRouteHandler } from '@mastra/next'
import { mastra } from '@/mastra'

export const { GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD } = createNextRouteHandler({
  mastra,
})
```

Mounted at `app/api/mastra/[...mastra]/route.ts`, pass `prefix: '/api/mastra'`. The app initializes lazily on first request. A2A tasks live in memory per instance.

### TanStack Start

```typescript
// src/routes/api/$.ts
import { createStartRouteHandler } from '@mastra/tanstack-start'
import { createFileRoute } from '@tanstack/react-router'
import { mastra } from '../../mastra'

export const Route = createFileRoute('/api/$')({
  server: {
    handlers: createStartRouteHandler({ mastra }),
  },
})
```

Exclude `@mastra/duckdb` and `execa` from `optimizeDeps` and mark `/^@duckdb\//` external in Nitro (see `mastra-framework-integration`).

---

## Custom adapters

Extend `MastraServer<TApp, TRequest, TResponse>` from `@mastra/server/server-adapter` and implement:

| Method | Job |
|---|---|
| `registerContextMiddleware()` | Attach `mastra`, a new `RequestContext`, `tools`, `abortSignal`, `taskStore` to each request. |
| `registerAuthMiddleware()` | Read `this.mastra.getServer()?.auth`. Return early if unset. Authenticate (401) and authorize (403). |
| `registerHttpLoggingMiddleware()` | Honor `this.httpLoggingConfig` and `this.shouldLogRequest(path)`. May be a no-op. |
| `registerRoute(app, route, { prefix })` | Map a `ServerRoute` to the framework router. Use `getParams`, `parseQueryParams`, `parseBody`, then `route.handler(params)`. |
| `getParams(route, request)` | Return `{ urlParams, queryParams, body }`. |
| `sendResponse(route, response, result)` | Write JSON or other non-stream results. |
| `stream(route, response, result)` | Write streaming results. |

Start from the Express or Hono adapter source when possible.
