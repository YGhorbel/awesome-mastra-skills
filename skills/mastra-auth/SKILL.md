---
name: mastra-auth
description: "Secure a Mastra server and Studio: server.auth with SimpleAuth, MastraJwtAuth, CompositeAuth, a custom MastraAuthProvider, or a provider package (Auth0, Better Auth, Clerk, Firebase, Google, Okta, Supabase, WorkOS, Neon), plus per-user memory isolation with mapUserToResourceId, public routes, RBAC, fine-grained authorization (FGA), and worker tokens. Use this skill whenever the user wants to require login or API keys for Mastra endpoints, pass tokens from a frontend, keep users from reading each other's threads, combine auth methods, map roles to permissions, or authenticate workers. Triggers on server.auth, authenticateToken, mapUserToResourceId, requiresAuth, SimpleAuth, MastraJwtAuth, @mastra/auth, CompositeAuth, MastraAuthProvider, @mastra/auth-clerk, @mastra/auth-auth0, @mastra/auth-supabase, @mastra/auth-firebase, @mastra/auth-workos, @mastra/auth-better-auth, @mastra/auth-okta, @mastra/auth-google, @mastra/auth-neon, server.rbac, server.fga, MASTRA_WORKER_AUTH_TOKEN, 401, 403."
license: Apache-2.0
metadata:
  category: server-and-frontend
  catalog_summary: "Server and Studio auth: SimpleAuth, JWT, composite, custom providers, identity providers, RBAC, FGA, workers"
  display_order: 5
  docs: https://mastra.ai/docs/auth/overview
---

# Mastra Auth

Authenticate callers to the Mastra server and Studio, carry their identity into agents and tools, and authorize what they can touch.

---

## When to use

- Turning on authentication for the built-in `/api` routes, custom routes, and Studio
- Choosing between SimpleAuth, JWT, an identity provider package, or a custom provider
- Supporting several auth methods at once (API keys plus user sessions)
- Isolating memory and threads per user or tenant
- Making a webhook or health route public
- Mapping identity-provider groups or roles to Mastra permissions (RBAC)
- Resource-level permissions for multi-tenant apps (FGA)
- Authenticating separate worker processes

## When NOT to use

- Middleware, CORS, and route plumbing in general (use `mastra-server`)
- Sending the token from a frontend or service (covered briefly here, details in `mastra-client-sdk`)
- MCP server OAuth and MCP tool auth context (use `mastra-mcp`)
- Studio deployment and its sign-in screens (use `mastra-studio-editor`)
- Worker process topology (use `mastra-deployment`)
- Thread and resource design for memory itself (use `mastra-memory`)

---

## Required inputs

- The identity system in use (none yet, Clerk, Auth0, Supabase, Firebase, WorkOS, Okta, Google Workspace, Better Auth, Neon Auth, or in-house)
- Who calls the server: browsers with sessions, services with API keys, workers, or several of these
- The ownership boundary for memory: per user, per organization, or per workspace and user
- Routes that must stay public (webhooks, health checks)
- Whether roles or per-resource permissions are needed, and whether an Enterprise Edition license applies in production (RBAC and FGA)

---

## The framework: authenticate, propagate, authorize

| Stage | Question | Mastra mechanism |
|---|---|---|
| Authenticate | Who is calling? | `server.auth` |
| Propagate | How does identity reach code? | `RequestContext` (`requestContext.get('user')`, `MASTRA_RESOURCE_ID_KEY`) |
| Authorize | What may they do? | `authorizeUser`, `server.rbac`, `server.fga`, checks in tools and routes |
| Outbound | Which credential calls another service? | Trusted tool code, never model input |

Once `server.auth` is set, built-in routes and custom routes require a valid user. Without it, every route and Studio is public.

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { MastraJwtAuth } from '@mastra/auth'

export const mastra = new Mastra({
  server: {
    auth: new MastraJwtAuth({
      secret: process.env.MASTRA_JWT_SECRET,
      mapUserToResourceId: user => user.id,
    }),
  },
})
```

`mapUserToResourceId` sets a server-owned resource ID after authentication. The server then filters thread lists, rejects cross-resource access with 403, and ignores a client-supplied `memory.resource`. Without it, any authenticated caller can read any resource's threads, and Mastra logs a startup warning.

### Picking a provider

| Need | Use |
|---|---|
| Local dev, static API keys, worker tokens | `SimpleAuth` from `@mastra/core/server` |
| Shared-secret JWTs | `MastraJwtAuth` from `@mastra/auth` |
| Hosted identity provider | `MastraAuth<Provider>` from `@mastra/auth-<provider>` (see `references/providers.md`) |
| Several methods at once | `CompositeAuth([a, b])` from `@mastra/core/server` |
| In-house tokens or SSO | Extend `MastraAuthProvider`, or pass `{ authenticateToken, mapUserToResourceId }` |

Studio login works with Simple Auth, JWT, WorkOS, Better Auth, and Google. Set `studio.auth` to give Studio its own provider.

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/` and the provider package docs and types. Otherwise fetch `https://mastra.ai/docs/auth/overview.md` and the provider page, for example `https://mastra.ai/reference/auth/clerk.md`. Trust these over memory.
2. **Pick the provider** with the table above. Install its package.
3. **Set env vars** the provider reads (see `references/providers.md`). Many providers work with an empty constructor once env vars are set.
4. **Configure `server.auth`** in `src/mastra/index.ts`. Add `mapUserToResourceId` whenever more than one user shares the deployment.
5. **Mark public routes.** Set `requiresAuth: false` on webhook routes and verify their signatures in the handler.
6. **Check the API prefix.** If `server.apiPrefix` changed, update `protected` and `public` paths on the provider.
7. **Send tokens from clients.** `MastraClient` `headers: { Authorization: 'Bearer <token>' }`, or `credentials: 'include'` for cookie sessions.
8. **Enforce ownership in tools.** Read `requestContext.get('user')` in `execute`, never an ID from tool input.
9. **Add RBAC or FGA** if roles or per-resource permissions are needed.
10. **Test** that anonymous calls get 401, wrong-user thread access gets 403, and allowed calls succeed.

---

## Deep dive: combining and customizing

`CompositeAuth` tries providers in order and returns the first user. Errors thrown in `authenticateToken()` are swallowed so the next provider gets a chance. `authorizeUser()` errors are not swallowed and fail the request with 500, so return `false` instead of throwing.

```typescript
import { CompositeAuth, SimpleAuth } from '@mastra/core/server'
import { MastraAuthClerk } from '@mastra/auth-clerk'

const apiKeyAuth = new SimpleAuth({
  tokens: { [process.env.CI_API_KEY!]: { id: 'ci', name: 'CI Pipeline' } },
})

const clerkAuth = new MastraAuthClerk({
  publishableKey: process.env.CLERK_PUBLISHABLE_KEY,
  secretKey: process.env.CLERK_SECRET_KEY,
  jwksUri: process.env.CLERK_JWKS_URI,
})

export const mastra = new Mastra({
  server: { auth: new CompositeAuth([clerkAuth, apiKeyAuth]) },
})
```

Put the most common method first. For a custom provider, extend `MastraAuthProvider`, call `super({ name })`, then `this.registerOptions(options)`, and implement `authenticateToken(token, request)` and `authorizeUser(user, request)`. `verifyJwks`, `verifyHmac`, and `decodeToken` from `@mastra/auth` cover common JWT checks. See `references/examples.md`.

---

## Failure patterns

- **No `mapUserToResourceId` in a multi-user app.** Users can list and read each other's threads. Add the mapper or set `MASTRA_RESOURCE_ID_KEY` in middleware.
- **Mapper returns an empty or non-string value.** Every authenticated request fails with 500. Return a stable non-empty string.
- **Custom `apiPrefix` with default auth paths.** Built-in routes fall outside `/api/*` and become public. Update `protected` and `public`.
- **Webhook rejected with 401.** Custom routes are protected by default. Set `requiresAuth: false` and verify the signature yourself.
- **Middleware meant to block a public route.** User middleware does not run on `requiresAuth: false` routes. Check inside the handler.
- **`401` from the browser after sign-in.** The token or cookie is not sent. Add the `Authorization` header or `credentials: 'include'` with a credentialed CORS origin.
- **Missing `Bearer ` prefix with providers that expect it.** Send `Authorization: Bearer <token>`. SimpleAuth accepts the token with or without the prefix, but providers such as Clerk require it.
- **SimpleAuth in production.** Tokens live in memory with no expiry or signature. Use JWT or an identity provider.
- **`MastraJwtAuth` throws at startup.** Neither `secret` nor `JWT_AUTH_SECRET` is set, or `secret` is an empty string.
- **Tool trusts a `userId` argument.** The model can choose any value. Read the user from request context.
- **Supabase or Firebase denies valid users.** The default `authorizeUser` checks `users.isAdmin` (Supabase) or a `user_access` document (Firebase). Override `authorizeUser`.
- **Workers split from the API with no auth.** Step execution and event endpoints are open. Configure `server.auth` and set `MASTRA_WORKER_AUTH_TOKEN` on workers.

---

## Output format

A finished auth setup contains:

- `server.auth` (and `studio.auth`, `server.rbac`, `server.fga` when needed) in `src/mastra/index.ts`
- `mapUserToResourceId` or equivalent middleware for multi-user deployments
- Public routes listed with the reason and signature verification
- Provider env vars in `.env.example` (never `.env`)
- Client code that sends the token or cookie
- Tests or `curl` checks for 401, 403, and success paths

---

## Reference files

- [`references/providers.md`](references/providers.md) - Every provider: package, class, constructor shape, env vars, default authorization, Studio and RBAC support.
- [`references/api.md`](references/api.md) - `server.auth` config, SimpleAuth, JWT, CompositeAuth, `MastraAuthProvider`, helpers, RBAC, FGA, worker auth.
- [`references/examples.md`](references/examples.md) - JWT with per-user memory, custom JWKS provider, tenant-safe tools, Okta RBAC, worker tokens.
- [`references/checklist.md`](references/checklist.md) - Pre-production auth checklist.

**Live docs**

- https://mastra.ai/docs/auth/overview
- https://mastra.ai/docs/auth/simple-auth
- https://mastra.ai/docs/auth/jwt
- https://mastra.ai/docs/auth/composite-auth
- https://mastra.ai/docs/auth/custom-auth-provider
- https://mastra.ai/docs/auth/fga
- https://mastra.ai/docs/auth/workers
- https://mastra.ai/docs/guides/authentication-identity
- https://mastra.ai/reference/auth/jwt
