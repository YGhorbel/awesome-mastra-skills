---
name: mastra-server
description: "Configure and extend the Mastra HTTP server: server options on new Mastra({ server }), built-in /api routes, custom routes with registerApiRoute or createRoute, Hono middleware, request context populated from headers, server adapters for Express, Hono, Fastify, Koa, Elysia, NestJS, Next.js, and TanStack Start, custom adapters, and the pub/sub event bus. Use this skill whenever the user wants to add an endpoint or webhook to a Mastra server, write middleware, set CORS, body size, timeouts, or an API prefix, mount Mastra inside an existing app, or run Mastra across several processes or hosts. Triggers on registerApiRoute, createRoute, @mastra/core/server, @mastra/server/server-adapter, MastraServer, @mastra/express, @mastra/hono, @mastra/fastify, @mastra/koa, @mastra/elysia, @mastra/nestjs, @mastra/next, @mastra/tanstack-start, server.middleware, server.cors, apiRoutes, startWorkers, RedisStreamsPubSub, UnixSocketPubSub, swagger-ui. Also triggers on Mastra endpoint 404, CORS, or 413 errors."
license: Apache-2.0
metadata:
  category: server-and-frontend
  catalog_summary: "Server config, built-in routes, custom routes, middleware, request context, server adapters, pub/sub"
  display_order: 1
  docs: https://mastra.ai/docs/server/overview
---

# Mastra Server

Configure the HTTP server that exposes agents, workflows, tools, and memory, add your own routes and middleware, and run Mastra inside another framework when needed.

---

## When to use

- Adding a custom endpoint, webhook, or health check to a Mastra server
- Writing server middleware (logging, header checks, CORS, request context injection)
- Setting `server` options: port, host, CORS, body size, timeout, Swagger UI, error hooks
- Mounting Mastra inside an existing Express, Hono, Fastify, Koa, Elysia, or NestJS app
- Exposing Mastra from a Next.js or TanStack Start catch-all route
- Choosing a pub/sub backend for multi-process or multi-host deployments
- Building an adapter for an unsupported HTTP framework

## When NOT to use

- Calling the server from a browser or another service (use `mastra-client-sdk`)
- Step-by-step setup in a specific framework such as Next.js or SvelteKit (use `mastra-framework-integration`)
- Chat routes for `useChat()`, `chatRoute()`, `handleChatStream()` (use `mastra-agentic-ui`)
- Authentication providers, JWT, RBAC, FGA (use `mastra-auth`)
- Deploying to Vercel, Cloudflare, or containers (use `mastra-deployment`)
- MCP server routes and MCP auth (use `mastra-mcp`)
- Per-request agent behavior such as dynamic instructions (use `mastra-agents`)

---

## Required inputs

- How the server runs: generated server (`mastra dev` / `mastra build`) or a server adapter in an existing app
- The framework and version if an adapter is involved
- The routes to add: path, method, body shape, and whether they need auth
- Values to derive per request (tenant, locale, user tier) and the header or token they come from
- Deployment shape: single process, several processes on one host, or several hosts

Ask before writing code if the serving mode is unclear. Middleware behaves differently on non-Hono adapters.

---

## The framework: one server, three extension points

Mastra serves a Hono app. `mastra build` generates it in `.mastra`. Server adapters mount the same routes on your framework instead. Built-in routes live under `/api` (agents, workflows, tools, memory, vectors, logs, MCP, and more). With `mastra dev`, browse them at `http://localhost:4111/swagger-ui` or `/api/openapi.json`.

You extend the server in three places:

| Extension | Where | Runs on |
|---|---|---|
| Custom routes | `server.apiRoutes` with `registerApiRoute()` or `createRoute()` | All serving paths |
| Middleware | `server.middleware` (Hono signature `(c, next)`) | Hono-based paths only |
| Request context | `c.get('requestContext').set(...)` inside middleware or routes | All paths |

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { registerApiRoute } from '@mastra/core/server'

export const mastra = new Mastra({
  server: {
    port: 3000, // Defaults to PORT env var or 4111
    middleware: [
      async (c, next) => {
        const country = c.req.header('CF-IPCountry')
        c.get('requestContext').set('temperature-unit', country === 'US' ? 'fahrenheit' : 'celsius')
        await next()
      },
    ],
    apiRoutes: [
      registerApiRoute('/health-check', {
        method: 'GET',
        handler: async c => c.json({ status: 'ok' }),
      }),
    ],
  },
})
```

Custom routes are mounted at the server root (`/health-check`), not under `/api`. Paths that start with the API prefix throw at startup.

### Generated server vs adapter

| Choose the generated server when | Choose an adapter when |
|---|---|
| Mastra is its own service | Mastra endpoints belong inside an existing app |
| You want `server.cors`, `server.port`, `apiRoutes` handled for you | You need control over middleware order or the HTTP framework |
| You use file-based agents | You register every agent in code |

Adapters ignore `port`, `host`, `cors`, `timeout`, and `apiRoutes` from `server` config. Configure those with the framework. They still read `auth`, `bodySizeLimit`, `onError`, and `middleware` (Hono-based only).

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/` and `node_modules/@mastra/server/dist/docs/` plus the installed types. Otherwise fetch `https://mastra.ai/docs/server/overview.md` and `https://mastra.ai/reference/server/register-api-route.md`. Trust these over memory.
2. **Pick the serving mode.** Generated server for a standalone service, or install the adapter package (`@mastra/express`, `@mastra/hono`, and so on).
3. **Set server options.** Port, host, CORS, `bodySizeLimit` (default 4.5 MB), `timeout` (default 3 minutes), `build.openAPIDocs` and `build.swaggerUI` for production docs.
4. **Add routes.** Use `registerApiRoute()` for Hono-style handlers. Use `createRoute()` from `@mastra/server/server-adapter` when you want Zod validation and typed handler params.
5. **Add middleware.** Put cross-cutting logic in `server.middleware`. Use `{ path, handler }` to scope it. On Express, Fastify, Koa, Elysia, or NestJS, register middleware with the framework instead.
6. **Populate request context.** Read headers or the authenticated user in middleware and `set()` values. Match them with `requestContextSchema` on agents and tools.
7. **Decide auth per route.** With `server.auth` configured, custom routes require auth. Set `requiresAuth: false` for public webhooks (see `mastra-auth`).
8. **With an adapter:** call `await server.init()`, then `await mastra.startWorkers()` after `listen`, and `await mastra.shutdown()` on `SIGTERM`.
9. **Choose pub/sub** if you run more than one instance (see deep dive).
10. **Test** with `curl` against the route and check `/api/openapi.json`.

---

## Deep dive: server adapters

```typescript
import express from 'express'
import { MastraServer } from '@mastra/express'
import { mastra } from './mastra'

const app = express()
app.use(express.json()) // Required for body parsing

const server = new MastraServer({ app, mastra })
await server.init()

const httpServer = app.listen(4111, async () => {
  try {
    await mastra.startWorkers()
  } catch (error) {
    console.error('Failed to start background workers', error)
    httpServer.close(() => process.exit(1))
  }
})

process.on('SIGTERM', async () => {
  await mastra.shutdown()
  process.exit(0)
})
```

`init()` runs `registerContextMiddleware()`, `registerAuthMiddleware()`, `registerUserMiddleware()`, then `registerRoutes()`. Routes added before `init()` have no Mastra context. Middleware added after `init()` never runs on Mastra routes. Call the steps by hand when you need custom ordering. Raw framework routes that need Mastra auth use the adapter's `createAuthMiddleware({ mastra })`.

Next.js and TanStack Start mount a catch-all route with `createNextRouteHandler({ mastra })` or `createStartRouteHandler({ mastra })`. The `prefix` must match the mount path. See `references/adapters.md`.

## Deep dive: pub/sub

Mastra uses one event bus for workflow execution, scheduled workflows, background tasks, agent signals, and resumable streams. The default `EventEmitterPubSub` is in process only.

| Deployment | Backend | Package |
|---|---|---|
| One process | `EventEmitterPubSub` (default) | `@mastra/core/events` |
| Several processes, one host | `UnixSocketPubSub` | `@mastra/core/events` |
| Several hosts | `RedisStreamsPubSub`, `ValkeyStreamsPubSub`, `GoogleCloudPubSub` | `@mastra/redis-streams`, `@mastra/valkey-streams`, `@mastra/google-cloud-pubsub` |

```typescript
import { Mastra } from '@mastra/core'
import { RedisStreamsPubSub } from '@mastra/redis-streams'

export const mastra = new Mastra({
  pubsub: new RedisStreamsPubSub({ url: 'redis://localhost:6379' }),
})
```

Wrap the in-process default in `CachingPubSub` to support stream replay on reconnect.

---

## Failure patterns

- **Custom route under `/api`.** Startup throws. Use `/webhooks/github`, not `/api/webhooks/github`, or change `server.apiPrefix` and update auth paths.
- **`server.middleware` on Express, Fastify, Koa, Elysia, or NestJS.** It is skipped with a warning. Register framework middleware, or use manual initialization.
- **Scheduled workflows never fire with an adapter.** `init()` does not start workers. Call `mastra.startWorkers()` after `listen`.
- **Express route returns an empty body.** `express.json()` is missing or added after `new MastraServer()`.
- **Setting `server.cors` or `server.port` with an adapter.** Ignored. Configure CORS and the port in the framework.
- **Middleware that blocks a public route.** User middleware never runs on `requiresAuth: false` routes. Authorize inside the handler.
- **Middleware path without the prefix.** With `apiPrefix: '/api/v2'`, block `/api/v2/memory/*`, not `/api/memory/*`.
- **Signals or workflow events lost across instances.** The default pub/sub is in process. Use Redis Streams, Valkey Streams, or Google Cloud Pub/Sub.
- **NestJS routes return 404.** `MastraModule` registers a catch-all controller. Import it last or mount it under a dedicated prefix.
- **Streaming route keeps running after the client leaves, or stops too early.** Pass `c.req.raw.signal` as `abortSignal` to cancel on disconnect. Omit it and call `consumeStream()` to keep generating.
- **Large uploads fail with 413.** Raise `server.bodySizeLimit` or set `maxBodySize` on a `createRoute()` route.

---

## Output format

A finished server change contains:

- `src/mastra/index.ts` with the `server` block (routes, middleware, options) or route modules imported into it
- For adapters: the app entry file with `MastraServer`, `init()`, `startWorkers()`, and shutdown handling
- Env vars (`PORT`, `MASTRA_HOST`, pub/sub URLs) listed in `.env.example`
- A `curl` command or test proving each new route responds with the expected status
- Notes on which routes are public and why

---

## Reference files

- [`references/api.md`](references/api.md) - Server config options, `registerApiRoute()`, `createRoute()`, `MastraServer` options, built-in route groups, pub/sub classes.
- [`references/adapters.md`](references/adapters.md) - Install, mount, context access, and quirks for each official adapter, plus custom adapters.
- [`references/examples.md`](references/examples.md) - Validated routes, tenant middleware, Hono adapter with manual init, persisted background stream.
- [`references/checklist.md`](references/checklist.md) - Pre-production server checklist.

**Live docs**

- https://mastra.ai/docs/server/overview
- https://mastra.ai/docs/server/custom-api-routes
- https://mastra.ai/docs/server/middleware
- https://mastra.ai/docs/server/request-context
- https://mastra.ai/docs/server/server-adapters
- https://mastra.ai/docs/server/custom-adapters
- https://mastra.ai/docs/server/pubsub
- https://mastra.ai/reference/server/routes
- https://mastra.ai/reference/configuration
