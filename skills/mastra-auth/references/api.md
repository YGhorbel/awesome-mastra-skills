# Auth API reference

Distilled from `https://mastra.ai/docs/auth/*.md`, `https://mastra.ai/reference/auth/jwt.md`, `https://mastra.ai/reference/auth/fga.md`, `https://mastra.ai/reference/configuration.md`, and `https://mastra.ai/docs/guides/authentication-identity.md`. Verify against installed types.

## Contents

- `server.auth` config object
- Route-level auth controls
- SimpleAuth
- MastraJwtAuth
- CompositeAuth
- MastraAuthProvider (custom)
- Token helpers
- Identity in request context
- RBAC
- FGA
- Worker auth

---

## `server.auth`

Type: `MastraAuthConfig | MastraAuthProvider`. Set `studio.auth` to give Studio its own provider; Studio requests then use it exclusively.

Inline config form:

| Field | Notes |
|---|---|
| `authenticateToken(token, request)` | Return the user or `null`. |
| `authorizeUser(user, request)` | Return `true` or `false` (403). |
| `mapUserToResourceId(user)` | Return a non-empty string. Sets `MASTRA_RESOURCE_ID_KEY`. Throwing or empty values fail the request with 500. |
| `protected` | `(RegExp \| string \| [string, Methods \| Methods[]])[]`. Default protects `/api/*`. |
| `public` | Same shape. Default `/api` and `/api/auth/*`. A route with `requiresAuth: true` still requires auth. |

Every provider class accepts `name`, `authorizeUser`, `protected`, `public`, and most accept `mapUserToResourceId`.

Behavior:

- No auth configured: all routes and Studio are public.
- Auth configured: built-in routes and custom routes require auth. A few built-in routes stay public, such as `GET /api/auth/capabilities`.
- Missing or invalid identity returns 401. Known identity without permission returns 403.

---

## Route-level controls

| Where | Control |
|---|---|
| `registerApiRoute(path, { requiresAuth: false })` | Public custom route. User middleware skips it. |
| `createRoute({ requiresAuth, fga })` | Auth and FGA metadata on typed routes. |
| Adapter `customRouteAuthConfig` | `Map<'METHOD:PATH', boolean>` overrides. |
| Adapter `createAuthMiddleware({ mastra, requiresAuth? })` | Mastra auth on raw framework routes. |
| `getAuthenticatedUser({ mastra, token, request })` from `@mastra/server/auth` | Resolve the user inside `server.middleware`, which runs before route auth. |

---

## SimpleAuth

Import: `import { SimpleAuth, getWebRequest } from '@mastra/core/server'`

| Option | Type | Notes |
|---|---|---|
| `tokens` | `Record<string, TUser>` | Required. Token to user map. |
| `headers` | `string \| string[]` | Extra headers to read. Defaults: `Authorization` (with or without `Bearer`), `X-Playground-Access`. |
| `name` | `string` | Logging. |
| `authorizeUser` | `(user, request) => boolean` | Use `getWebRequest(request)` to read the URL. |
| `protected`, `public` | Path patterns | |

Limits: in-memory tokens, no expiry, no signature check, all tokens known at startup.

---

## MastraJwtAuth

Import: `import { MastraJwtAuth } from '@mastra/auth'`

| Option | Default | Notes |
|---|---|---|
| `secret` | `process.env.JWT_AUTH_SECRET` | HMAC secret. Throws if unresolved or `''` (an empty string does not fall back). |
| `mapUserToResourceId` | | As above. |

The docs' examples read `MASTRA_JWT_SECRET` and pass it explicitly. Clients send `Authorization: Bearer <jwt>`.

---

## CompositeAuth

Import: `import { CompositeAuth } from '@mastra/core/server'`

`new CompositeAuth([providerA, providerB])`:

- Authentication: tries each `authenticateToken()` in order. First user wins. Thrown errors are caught and the next provider runs. All fail: 401.
- Authorization: calls each `authorizeUser()` until one returns `true`. A throw stops the chain with 500.
- `mapUserToResourceId` validation applies to the provider that authenticated the request.

---

## MastraAuthProvider (custom)

Import: `import { MastraAuthProvider, getRequestHeader, getWebRequest } from '@mastra/core/server'` and types `MastraAuthProviderOptions`, `MastraAuthRequest`.

```typescript
export class MyAuthProvider extends MastraAuthProvider<MyUser> {
  constructor(options?: MyAuthOptions) {
    super({ name: options?.name ?? 'my-auth' })
    // read config...
    this.registerOptions(options) // applies authorizeUser, protected, public
  }

  async authenticateToken(token: string, request: MastraAuthRequest): Promise<MyUser | null> {
    // token comes from Authorization: Bearer <token>
  }

  async authorizeUser(user: MyUser, request: MastraAuthRequest): Promise<boolean> {
    return !!user?.id
  }
}
```

Path patterns: exact (`'/health'`), wildcard (`'/api/*'`), regex (`/^\/secure\/.*/`), method-scoped (`['/api/webhook', 'POST']`).

---

## Token helpers

Import from `@mastra/auth`:

| Helper | Purpose |
|---|---|
| `verifyHmac(token, secret)` | Verify an HMAC-signed JWT. Returns the payload. |
| `verifyJwks(token, jwksUri)` | Verify against a JWKS endpoint. |
| `decodeToken(token)` | Decode without verifying. |
| `getTokenIssuer(decoded)` | Read the issuer. |
| `JwtPayload` (type) | Standard claims (`sub`, `iss`, `exp`, ...). |

---

## Identity in request context

| Value | How to read | Notes |
|---|---|---|
| Authenticated user | `requestContext.get('user')` | Set by auth before handlers run. |
| Resource ID | `MASTRA_RESOURCE_ID_KEY` | Set by `mapUserToResourceId` or middleware. Overrides client values. |
| Thread ID | `MASTRA_THREAD_ID_KEY` | Pin a validated thread. |
| Raw token | `MASTRA_AUTH_TOKEN_KEY` | For outbound calls to services that accept the caller's token. Keep out of prompts. |

Reserved keys (prefixed `mastra__` or `__mastra_`) are omitted from tracing spans and score records. `RequestContext` is not global: pass it explicitly when calling agents or workflows outside a request.

---

## RBAC

`server.rbac` takes a provider such as `MastraRBACOkta`, `MastraRBACGoogle`, or `MastraRBACNeon` with a `roleMapping` of role to permission patterns (`'*'`, `'agents:*'`, `'agents:read'`, `_default`). Enterprise Edition license required in production. Studio enforces RBAC when configured.

---

## FGA

`server.fga` takes an `IFGAProvider`, for example `MastraFGAWorkos` from `@mastra/auth-workos`. Enterprise Edition license required in production.

| Option (`MastraFGAWorkos`) | Notes |
|---|---|
| `resourceMapping` | `{ agent \| workflow \| thread \| <custom>: { fgaResourceType, deriveId?(ctx) } }`. `deriveId` gets `user`, `resourceId`, `requestContext`. Return `undefined` to use the Mastra ID. |
| `permissionMapping` | Mastra permission to provider slug, for example `[MastraFGAPermissions.AGENTS_EXECUTE]: 'manage-workflows'`. Unmapped strings pass through. |
| `requireForProtectedRoutes` | Deny protected routes without FGA metadata. |
| `auditProtectedRoutes` | `'warn' \| 'error'`. |
| `validatePermissions(permissions)` | Throw at startup when a mapping is missing. |
| `resolveRouteFGA` | `FGARouteResolver` for central route metadata. |

Imports: `MastraFGAPermissions`, `FGADeniedError`, types `IFGAProvider`, `FGACheckParams`, `FGARouteConfig`, `FGARouteResolver`, `ActorSignal` from `@mastra/core/auth/ee`.

Enforced permissions: `agents:execute`, `workflows:execute`, `tools:execute`, `memory:read`, `memory:write`, `memory:delete`, plus stored resource and per-route permissions. Direct `createRun().start()`, `resume()`, `restart()` calls are not checked by core FGA.

Custom provider: implement `check(user, params)`, `require(user, params)` (throw `FGADeniedError`), `filterAccessible(user, resources, resourceType, permission)`, optional `requireActor(actor, params)`.

`server.storedResources: { scope: true }` (or `{ metadataKey, resolve, requireScope }`) filters stored resources by `MASTRA_RESOURCE_ID_KEY`.

System actors: pass `actor: true` or `{ actorKind: 'system', propagate? }` from trusted server code. Built-in agent HTTP routes strip `actor` from client input.

---

## Worker auth

| Endpoint | Caller |
|---|---|
| `POST /api/workflows/:workflowId/runs/:runId/steps/execute` | Orchestration worker (`HttpRemoteStrategy`) |
| `POST /api/workflows/events` | Push-mode brokers |

Both have `requiresAuth: true`. Set `MASTRA_WORKER_AUTH_TOKEN` on workers (sent as `Bearer`). `HttpRemoteStrategy` from `@mastra/core/worker` also supports `auth: { type: 'api-key', key }` (header `x-worker-api-key`) and `auth: { type: 'header', name, value }`.
