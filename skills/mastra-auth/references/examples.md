# Auth examples

All examples follow the current auth docs. Verify provider options against the installed package.

## Contents

1. JWT auth with per-tenant memory and a public webhook
2. Custom JWKS provider
3. Tenant-safe tools
4. Okta login with RBAC
5. Worker token with SimpleAuth

---

## 1. JWT auth with per-tenant memory and a public webhook

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { registerApiRoute } from '@mastra/core/server'
import { MastraJwtAuth } from '@mastra/auth'

export const mastra = new Mastra({
  server: {
    auth: new MastraJwtAuth({
      secret: process.env.MASTRA_JWT_SECRET,
      mapUserToResourceId: user => `${user.orgId}:${user.id}`,
    }),
    apiRoutes: [
      // Protected by default
      registerApiRoute('/me', {
        method: 'GET',
        handler: async c => c.json({ user: c.get('requestContext').get('user') }),
      }),
      // Public: verify the sender's signature before trusting the body
      registerApiRoute('/webhooks/github', {
        method: 'POST',
        requiresAuth: false,
        handler: async c => {
          const payload = await c.req.json()
          return c.json({ received: true })
        },
      }),
    ],
  },
})
```

Client:

```typescript
import { MastraClient } from '@mastra/client-js'

export const mastraClient = new MastraClient({
  baseUrl: 'https://<mastra-api-url>',
  headers: { Authorization: `Bearer ${process.env.MASTRA_JWT_TOKEN}` },
})
```

Check it:

```bash
curl -i http://localhost:4111/api/agents                                   # 401
curl -i -H "Authorization: Bearer $MASTRA_JWT_TOKEN" http://localhost:4111/api/agents  # 200
```

---

## 2. Custom JWKS provider

```typescript
// src/mastra/auth/my-jwks-auth.ts
import { MastraAuthProvider } from '@mastra/core/server'
import type { MastraAuthProviderOptions } from '@mastra/core/server'
import { verifyJwks } from '@mastra/auth'
import type { JwtPayload } from '@mastra/auth'

type MyUser = JwtPayload

interface MyJwksAuthOptions extends MastraAuthProviderOptions<MyUser> {
  jwksUri?: string
  issuer?: string
}

export class MyJwksAuth extends MastraAuthProvider<MyUser> {
  protected jwksUri: string
  protected issuer: string

  constructor(options?: MyJwksAuthOptions) {
    super({ name: options?.name ?? 'my-jwks-auth' })
    const jwksUri = options?.jwksUri ?? process.env.MY_JWKS_URI
    if (!jwksUri) throw new Error('JWKS URI is required')
    this.jwksUri = jwksUri
    this.issuer = options?.issuer ?? process.env.MY_AUTH_ISSUER ?? ''
    this.registerOptions(options)
  }

  async authenticateToken(token: string): Promise<MyUser | null> {
    try {
      const payload = await verifyJwks(token, this.jwksUri)
      if (this.issuer && payload.iss !== this.issuer) return null
      return payload
    } catch {
      return null
    }
  }

  async authorizeUser(user: MyUser): Promise<boolean> {
    if (user.exp && user.exp * 1000 < Date.now()) return false
    return !!user.sub
  }
}
```

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { MyJwksAuth } from './auth/my-jwks-auth'

export const mastra = new Mastra({
  server: {
    auth: new MyJwksAuth({
      public: ['/health', ['/webhooks/billing', 'POST']],
    }),
  },
})
```

---

## 3. Tenant-safe tools

The model chooses `status`. Trusted code chooses the owner and the downstream credential.

```typescript
import { createTool } from '@mastra/core/tools'
import { z } from 'zod'
import { orders } from '../lib/orders'

export const listOrders = createTool({
  id: 'list-orders',
  description: 'List orders owned by the authenticated user',
  inputSchema: z.object({ status: z.enum(['open', 'shipped']).optional() }),
  execute: async ({ status }, { requestContext }) => {
    const user = requestContext.get('user') as { id: string } | undefined
    if (!user?.id) throw new Error('Authenticated user is missing')
    return orders.list({ ownerId: user.id, status })
  },
})
```

```typescript
import { createTool } from '@mastra/core/tools'
import { z } from 'zod'
import { billing, tenantCredentials } from '../lib/billing'

export const listInvoices = createTool({
  id: 'list-invoices',
  description: 'List invoices for the authenticated tenant',
  inputSchema: z.object({ limit: z.number().int().min(1).max(100).default(20) }),
  execute: async ({ limit }, { requestContext }) => {
    const user = requestContext.get('user') as { organizationId: string } | undefined
    if (!user?.organizationId) throw new Error('Authenticated organization is missing')
    const credential = await tenantCredentials.getBillingToken(user.organizationId)
    return billing.listInvoices({ limit, token: credential.token })
  },
})
```

---

## 4. Okta login with RBAC

```typescript
import { Mastra } from '@mastra/core'
import { MastraAuthOkta, MastraRBACOkta } from '@mastra/auth-okta'

export const mastra = new Mastra({
  server: {
    auth: new MastraAuthOkta(), // reads OKTA_DOMAIN, OKTA_CLIENT_ID, OKTA_CLIENT_SECRET, OKTA_REDIRECT_URI
    rbac: new MastraRBACOkta({
      roleMapping: {
        Admin: ['*'],
        Engineering: ['agents:*', 'workflows:*', 'tools:*'],
        Viewer: ['agents:read', 'workflows:read'],
        _default: [],
      },
    }),
  },
})
```

`.env.example`:

```bash
OKTA_DOMAIN=dev-123456.okta.com
OKTA_CLIENT_ID=your-client-id
OKTA_CLIENT_SECRET=your-client-secret
OKTA_REDIRECT_URI=http://localhost:4111/api/auth/callback
OKTA_COOKIE_PASSWORD=a-random-string-at-least-32-characters-long
OKTA_API_TOKEN=your-api-token
```

RBAC needs an Enterprise Edition license in production.

---

## 5. Worker token with SimpleAuth

```typescript
import { Mastra } from '@mastra/core/mastra'
import { CompositeAuth, SimpleAuth } from '@mastra/core/server'
import { MastraAuthClerk } from '@mastra/auth-clerk'

const workerAuth = new SimpleAuth({
  tokens: {
    [process.env.WORKER_TOKEN!]: { id: 'worker', name: 'Orchestration Worker', role: 'worker' },
  },
})

export const mastra = new Mastra({
  server: {
    auth: new CompositeAuth([new MastraAuthClerk(), workerAuth]),
  },
})
```

```yaml
services:
  api:
    environment:
      WORKER_TOKEN: ${WORKER_TOKEN}
  orchestration-worker:
    environment:
      MASTRA_WORKER_AUTH_TOKEN: ${WORKER_TOKEN}
      MASTRA_STEP_EXECUTION_URL: http://api:4111/api # HTTPS in production
```

Use one token per worker type so you can revoke them separately.
