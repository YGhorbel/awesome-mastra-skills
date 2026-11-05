# Server API reference

Distilled from `https://mastra.ai/reference/configuration.md`, `https://mastra.ai/reference/server/register-api-route.md`, `https://mastra.ai/reference/server/create-route.md`, `https://mastra.ai/reference/server/mastra-server.md`, `https://mastra.ai/reference/server/routes.md`, and `https://mastra.ai/reference/pubsub/base.md`. Verify against the installed version.

## Contents

- Server options on `new Mastra({ server })`
- `registerApiRoute()`
- `createRoute()`
- Request context and reserved keys
- `MastraServer` adapter options and methods
- Built-in route groups
- Pub/sub classes

---

## Server options: `new Mastra({ server: {...} })`

| Option | Type | Default | Notes |
|---|---|---|---|
| `port` | `number` | `4111` or `PORT` | Generated server only. |
| `host` | `string` | `localhost` or `MASTRA_HOST` | Generated server only. |
| `apiRoutes` | `ApiRoute[]` | | From `registerApiRoute()` or `createRoute()`. |
| `middleware` | `Middleware \| Middleware[]` | | Function `(c, next)` or `{ path, handler }`. Hono-based paths only. |
| `auth` | `MastraAuthConfig \| MastraAuthProvider` | | See `mastra-auth`. |
| `cors` | `CorsOptions \| false` | see below | `false` disables CORS. Generated server only. |
| `bodySizeLimit` | `number` (bytes) | `4_718_592` (4.5 MB) | Read by adapters too. |
| `timeout` | `number` (ms) | `180000` | Independent of a serverless platform's own limit. |
| `build` | `{ swaggerUI, apiReqLogs, openAPIDocs }` | all `false` | Production toggles. `swaggerUI` needs `openAPIDocs`. |
| `onError` | `(err, c) => Response` | | Unhandled route errors. All adapters (shim context on non-Hono). |
| `onValidationError` | `(error, context) => { status, body } \| undefined` | 400 | `context` is `'query' \| 'body' \| 'path'`. Route-level hook wins. |
| `https` | `{ key: Buffer; cert: Buffer }` | | Dev TLS. Or `mastra dev --https`. |
| `studioBase` | `string` | `/` | Host Studio on a sub-path. |
| `drainTimeout` | `number` (ms) | `5000` | HTTP drain, then workflow drain. Worst case twice this plus 5 s. |
| `handleShutdownSignals` | `boolean` | `true` | Set `false` to install your own `SIGINT`/`SIGTERM` handlers. |
| `mcpOptions` | `{ setRequestAuth, serverless, sessionIdGenerator }` | | `setRequestAuth(req, requestContext)` sets `req.auth` for MCP tools. |
| `apiPrefix` | `string` | `/api` | Prefix for built-in routes. Update auth `protected`/`public` paths and client `apiPrefix` when you change it. |

`cors` fields: `origin` (`'*'`), `allowMethods` (`GET, POST, PUT, PATCH, DELETE, OPTIONS`), `allowHeaders` (`Content-Type, Authorization, x-mastra-client-type, x-mastra-dev-playground`), `exposeHeaders` (`Content-Length, X-Requested-With`), `credentials` (`false`), `maxAge` (`3600`).

Top-level (not under `server`): `pubsub` (default `EventEmitterPubSub`), `bundler.externals`.

---

## `registerApiRoute(path, options)`

Import: `import { registerApiRoute } from '@mastra/core/server'`

`path` supports `:param` segments. It can't start with the configured `apiPrefix`.

| Option | Type | Notes |
|---|---|---|
| `method` | `'GET' \| 'POST' \| 'PUT' \| 'DELETE' \| 'PATCH' \| 'ALL'` | Required. |
| `handler` | `(c: Context) => Response` | Hono context. Use `handler` or `createHandler`, not both. |
| `createHandler` | `({ mastra }) => Promise<handler>` | Runs once at startup for async setup. |
| `middleware` | `MiddlewareHandler \| MiddlewareHandler[]` | Route-only middleware. |
| `cors` | `CorsOptions` | Route-specific CORS policy. |
| `openapi` | `DescribeRouteOptions` | `summary`, `description`, `tags` (default `['custom']`), `deprecated`, `parameters`, `requestBody`, `responses`, `security`. Zod schemas are converted. Routes without it are not listed in Swagger UI. |
| `requiresAuth` | `boolean` | Default `true` when `server.auth` is set. `false` makes the route public. |

Handler context: `c.get('mastra')`, `c.get('requestContext')`, `c.req.param('id')`, `c.req.query('q')`, `await c.req.json()`, `c.req.raw.signal`, return `c.json(data, status)`. Throw `HTTPException` from `hono/http-exception` for status errors.

---

## `createRoute(config)`

Import: `import { createRoute } from '@mastra/server/server-adapter'`

| Field | Notes |
|---|---|
| `method`, `path` | Required. |
| `responseType` | `'json' \| 'stream'`. |
| `streamFormat` | `'sse' \| 'stream'` when streaming. |
| `handler` | Receives validated fields flattened plus `mastra`, `requestContext`, `registeredTools`, `abortSignal`, `taskStore`. |
| `pathParamSchema`, `queryParamSchema`, `bodySchema` | Zod. Use `z.coerce` for query numbers, booleans, dates. |
| `responseSchema` | Documents the response for OpenAPI. |
| `maxBodySize` | Per-route byte limit. |
| `summary`, `description`, `tags`, `deprecated` | OpenAPI metadata. |
| `onValidationError` | Per-route override of the server hook. |
| `requiresAuth`, `fga` | Auth and FGA metadata (see `mastra-auth`). |

Returns a `ServerRoute`. Pass it in `server.apiRoutes` or register it with an adapter.

---

## Request context

Import: `import { RequestContext, MASTRA_RESOURCE_ID_KEY, MASTRA_THREAD_ID_KEY, MASTRA_SCOPES_KEY } from '@mastra/core/request-context'`

| Method | Notes |
|---|---|
| `set(key, value)`, `get(key)`, `has`, `delete` | Typed when declared with a generic or `requestContextSchema`. |
| `setRaw`, `getRaw`, `hasRaw`, `deleteRaw` | Keys outside the schema. Values are `unknown`. |
| `all`, `keys()`, `entries()` | Whole object and iterators. |

| Reserved key | Effect |
|---|---|
| `MASTRA_RESOURCE_ID_KEY` | Forces memory operations to this resource. Cross-resource access returns 403. |
| `MASTRA_THREAD_ID_KEY` | Forces thread operations to this thread. |
| `MASTRA_SCOPES_KEY` | `<type>:<value>` scopes the run acts as. Does not drive ownership checks by itself. |
| `MASTRA_MESSAGE_AUTHOR_KEY` | `{ id, name?, avatarUrl? }` author of a user message. |

`getAuthenticatedUser({ mastra, token, request })` from `@mastra/server/auth` resolves the user inside middleware, which runs before per-route auth.

Studio presets: `mastra dev --request-context-presets ./presets.json`.

---

## `MastraServer` (adapters)

Import from the adapter package (`@mastra/express`, `@mastra/hono`, `@mastra/fastify`, `@mastra/koa`, `@mastra/elysia`) or extend the abstract class from `@mastra/server/server-adapter`.

| Option | Default | Notes |
|---|---|---|
| `app` | | Framework app. Required. |
| `mastra` | | Mastra instance. Required. |
| `prefix` | `'/api'` | Built-in route prefix. |
| `openapiPath` | `''` | Serve the OpenAPI spec, for example `/openapi.json`. |
| `bodyLimitOptions` | | `{ maxSize, onError }`. |
| `streamOptions` | `{ redact: true }` | Redacts system prompts, tool definitions, and keys from streamed chunks. |
| `customRouteAuthConfig` | | `Map<'METHOD:PATH', boolean>`. Wildcards allowed. `false` is public. Methods: `GET`, `POST`, `PUT`, `DELETE`, `ALL`. |
| `tools` | | Extra tools. |
| `taskStore` | | A2A task store. |
| `mcpOptions` | | `setRequestAuth`, `serverless`, `sessionIdGenerator`. |

Methods: `init()`, `registerContextMiddleware()`, `registerAuthMiddleware()`, `registerUserMiddleware()`, `registerRoutes()`, `getApp()`. Also `mastra.getServerApp()`. Abstract methods for custom adapters: `registerContextMiddleware`, `registerAuthMiddleware`, `registerHttpLoggingMiddleware`, `registerRoute`, `getParams`, `sendResponse`, `stream`.

Instance lifecycle: `await mastra.startWorkers()` (idempotent) and `await mastra.shutdown()`.

---

## Built-in route groups

All prefixed with `/api` by default. Full list: `https://mastra.ai/reference/server/routes`.

| Group | Examples |
|---|---|
| Agents | `GET /api/agents`, `POST /api/agents/:agentId/generate`, `/stream`, `/send-message`, `/resume-stream`, `/tools/:toolId/execute` |
| Workflows | `GET /api/workflows`, `POST /api/workflows/:workflowId/create-run`, `/start-async`, `/stream`, `/resume`, `GET /runs/:runId` |
| Tools | `GET /api/tools`, `POST /api/tools/:toolId/execute` |
| Memory | `GET/POST /api/memory/threads`, `/threads/:threadId/messages`, `/clone` |
| Vectors | `POST /api/vectors/:vectorName/upsert`, `/query`, `/delete` |
| Datasets, scores, logs, telemetry | `/api/datasets`, `/api/experiments`, `/api/scores`, `/api/logs`, `/api/telemetry/traces` |
| MCP | `ALL /api/mcp/:serverId/mcp`, `/api/mcp/v0/servers` |
| Responses, Conversations | `POST /api/v1/responses`, `/api/v1/conversations` (experimental) |

Errors use `{ error: string, details?: unknown }` with 400, 401, 403, 404, 500.

---

## Pub/sub

| Class | Import | Constructor |
|---|---|---|
| `EventEmitterPubSub` | `@mastra/core/events` | `new EventEmitterPubSub(existingEmitter?, options?)` |
| `UnixSocketPubSub` | `@mastra/core/events` | `new UnixSocketPubSub('/tmp/mastra/events.sock')` |
| `CachingPubSub` | `@mastra/core/events` | `new CachingPubSub(inner, cache)` with `InMemoryServerCache` from `@mastra/core/cache`, or `withCaching(inner, cache)` |
| `RedisStreamsPubSub` | `@mastra/redis-streams` | `{ url, keyPrefix, blockMs, cluster, client, maxStreamLength, streamIdleTtlMs, reclaimIntervalMs, reclaimIdleMs, maxDeliveryAttempts, inFlightTimeoutMs }` |
| `ValkeyStreamsPubSub` | `@mastra/valkey-streams` | `{ url, valkeyOptions, keyPrefix, ... }` (same tuning fields as Redis) |
| `GoogleCloudPubSub` | `@mastra/google-cloud-pubsub` | `{ projectId, ... }` client config |
| `PubSub` (abstract) | `@mastra/core/events` | Implement `publish`, `subscribe`, `unsubscribe`, `flush` |

Redis defaults: `url` `redis://localhost:6379`, `keyPrefix` `mastra:topic`, `maxStreamLength` 10000, `streamIdleTtlMs` 7 days, `maxDeliveryAttempts` 5. `RedisStreamsPubSub` provides leases across hosts for durable agent recovery. `GoogleCloudPubSub` does not.
