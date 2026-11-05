# Server checklist

Run this before calling a server change done.

## Configuration

- [ ] Serving mode chosen and documented: generated server or a named adapter
- [ ] `port` and `host` set through env (`PORT`, `MASTRA_HOST`) for the generated server, or in the framework's `listen` for adapters
- [ ] CORS restricted to known origins in production (`server.cors` or framework CORS); no `'*'` with credentials
- [ ] `bodySizeLimit` and `timeout` sized for the largest real request; serverless function limits raised to match
- [ ] `build.openAPIDocs` and `build.swaggerUI` enabled only if the API docs should be public
- [ ] `onError` reports to your error tracker and does not leak stack traces

## Routes

- [ ] No custom route path starts with the API prefix
- [ ] Each route has a clear auth decision: default protected, or `requiresAuth: false` with a reason
- [ ] Public webhooks verify the sender's signature before trusting the body
- [ ] Input validated with `createRoute()` schemas or explicit checks
- [ ] Streaming routes decide on disconnect behavior: forward `c.req.raw.signal` or `consumeStream()`
- [ ] Unused built-in route groups blocked with middleware if they should not be reachable

## Middleware and request context

- [ ] Middleware runs on the serving path in use (Hono-based) or is ported to the framework
- [ ] Middleware paths include the configured prefix
- [ ] Values set in request context match `requestContextSchema` on agents, tools, and workflows
- [ ] Ownership keys (`MASTRA_RESOURCE_ID_KEY`, `MASTRA_THREAD_ID_KEY`) come only from verified identity

## Adapters

- [ ] Body parser registered before `MastraServer` (Express, Koa)
- [ ] `await server.init()` before routes that need Mastra context
- [ ] `await mastra.startWorkers()` after `listen`, unless workers run in a separate process
- [ ] `mastra.shutdown()` wired to `SIGTERM`
- [ ] NestJS: `MastraModule` imported last or mounted under its own prefix
- [ ] Next.js and TanStack Start: `prefix` matches the catch-all mount path

## Multi-instance

- [ ] Pub/sub backend matches the topology: `UnixSocketPubSub` for one host, Redis Streams, Valkey Streams, or Google Cloud Pub/Sub across hosts
- [ ] Redis or Valkey `streamIdleTtlMs` exceeds the longest worker downtime
- [ ] Every new route verified with `curl` or a test, including 401 and 404 cases
