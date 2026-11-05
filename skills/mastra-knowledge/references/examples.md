# Knowledge examples

All examples follow the current docs. Knowledge is alpha, so check the installed version first.

## Contents

1. Read-only docs agent with seeded content
2. One support agent, many customers
3. A policy pinned for every support run
4. Access tests with explainAccess()
5. Studio browsing with auth

---

## 1. Read-only docs agent with seeded content

```typescript
// src/mastra/knowledge.ts
import { Knowledge, knowledgeMemoryScopes } from '@mastra/core/knowledge'
import { ModelRouterEmbeddingModel } from '@mastra/core/llm'
import { LibSQLStore, LibSQLVector } from '@mastra/libsql'

export const knowledge = new Knowledge({
  id: 'docs',
  storage: new LibSQLStore({ id: 'knowledge', url: 'file:./knowledge.db' }),
  vector: new LibSQLVector({ id: 'knowledge-vector', url: 'file:./knowledge.db' }),
  embedder: new ModelRouterEmbeddingModel('openai/text-embedding-3-small'),
  tools: { read: { maxTokens: 3000 } },
  scopes: {
    ...knowledgeMemoryScopes(),
    'docs:$orgId': {
      description: 'Product docs',
      belongsTo: 'org:$orgId',
      access: [{ principal: 'org:$orgId', role: 'viewer' }],
    },
  },
})
```

```typescript
// src/mastra/seed-docs.ts (trusted server code only)
import { knowledge } from './knowledge'

type Doc = { slug: string; title: string; markdown: string }

export async function seedDocs(orgId: string, docs: Doc[]) {
  for (const doc of docs) {
    await knowledge.upsertPage({
      scope: `docs:${orgId}`,
      path: doc.slug, // 'guides/install' becomes docs:acme#guides/install
      name: doc.title,
      body: doc.markdown,
      author: 'seed:docs',
    })
  }
}
```

```typescript
// src/mastra/agents/docs-agent.ts
import { Agent } from '@mastra/core/agent'
import { knowledge } from '../knowledge'

export const docsAgent = new Agent({
  id: 'docs-agent',
  name: 'Docs agent',
  instructions: 'Answer product questions from the docs. Say so when the docs do not cover it.',
  model: 'openai/gpt-6.1-sol',
  knowledge,
})

await docsAgent.generate('How do I install the CLI?', { scopes: ['org:acme'] })
```

Re-running `seedDocs` skips unchanged pages and does not re-embed them.

---

## 2. One support agent, many customers

```typescript
import { Knowledge, knowledgeMemoryScopes } from '@mastra/core/knowledge'
import { Agent } from '@mastra/core/agent'
import { Memory } from '@mastra/memory'
import { LibSQLStore } from '@mastra/libsql'

const storage = new LibSQLStore({ id: 'storage', url: 'file:./mastra.db' })

export const knowledge = new Knowledge({
  id: 'support',
  storage,
  tools: true,
  scopes: { ...knowledgeMemoryScopes({ org: 'tenant:$tenantId' }) },
})

export const supportAgent = new Agent({
  id: 'support-agent',
  name: 'Support agent',
  instructions: 'Help customers. Record durable account facts as notes.',
  model: 'openai/gpt-6.1-sol',
  memory: new Memory({ storage }),
  knowledge,
})

// Server code, after authenticating the user
await supportAgent.generate(message, {
  scopes: [`tenant:${tenantId}`],
  memory: { resource: userId, thread: threadId },
})
```

The run also holds `resource:<userId>` and `thread:<threadId>` from `memory`. A Globex run cannot find `tenant:acme` pages. The alpha does not guarantee isolation, so keep sensitive customer data elsewhere.

---

## 3. A policy pinned for every support run

```typescript
import { Knowledge, knowledgeMemoryScopes } from '@mastra/core/knowledge'
import { LibSQLStore } from '@mastra/libsql'

export const knowledge = new Knowledge({
  id: 'acme',
  storage: new LibSQLStore({ id: 'knowledge', url: 'file:./mastra.db' }),
  tools: true,
  pinnedContext: { maxTokens: 1000 },
  scopes: {
    ...knowledgeMemoryScopes(),
    'role:$orgId:support': {
      description: 'Customer support agents',
      pinnedContext: ['policy:$orgId#refund-policy'],
    },
    'policy:$orgId': {
      description: 'Company policies',
      access: [{ principal: 'org:$orgId', role: 'viewer' }],
      pages: [{ key: 'refund-policy', name: 'Refund Policy', description: 'Refund limits and approvals' }],
    },
  },
})

// Write the body from the server. Support runs are only viewers.
await knowledge.upsertPage({
  scope: 'policy:acme',
  path: 'refund-policy',
  name: 'Refund Policy',
  body: 'Refunds up to $500 need no approval. Above that, ask a lead.',
})

// The agent needs Memory for pins to reach it
await supportAgent.generate('A customer wants $700 back.', {
  scopes: ['org:acme', 'role:acme:support'],
  memory: { resource: 'dana', thread: 'ticket-91' },
})
```

Pinned pages arrive as a state signal: the full snapshot on the first turn, only changes after that. Agents cannot unpin config pins.

---

## 4. Access tests with explainAccess()

```typescript
import { describe, expect, it } from 'vitest'
import { knowledge } from './knowledge'

const roleOn = async (scopes: string[], scope: string) =>
  (await knowledge.explainAccess(scopes, { scope })).role

describe('team access', () => {
  it('lets a team edit its own scope', async () => {
    expect(await roleOn(['org:acme', 'team:acme:support'], 'team:acme:support')).toBe('editor')
  })
  it('lets the org read it', async () => {
    expect(await roleOn(['org:acme'], 'team:acme:support')).toBe('viewer')
  })
  it('hides it from another org', async () => {
    expect(await roleOn(['org:globex'], 'team:acme:support')).toBeNull()
  })
})
```

Rules that bind through `belongsTo` give no role until a writing run places the scope. Test those after a write.

---

## 5. Studio browsing with auth

```typescript
import { Mastra } from '@mastra/core/mastra'
import { KNOWLEDGE_ROUTES, MASTRA_KNOWLEDGE_PRINCIPALS_KEY } from '@mastra/server/server-adapter'
import { knowledge } from './knowledge'
import { supportAgent } from './agents/support-agent'
import { appAuthorize } from './auth'

export const mastra = new Mastra({
  agents: { supportAgent },
  knowledge: { company: knowledge },
  server: {
    apiRoutes: [...KNOWLEDGE_ROUTES],
    auth: {
      // authenticateToken, ...
      authorize: async (path, method, user, context) => {
        if (path.startsWith('/api/knowledge')) {
          context
            .get('requestContext')
            .set(
              MASTRA_KNOWLEDGE_PRINCIPALS_KEY,
              user.isAdmin ? 'all' : [`org:${user.orgId}`, `team:${user.orgId}:${user.teamId}`],
            )
          return true
        }
        return appAuthorize(path, method, user, context)
      },
    },
  },
})
```

Keep your app's existing decision for other paths. Returning `true` for everything lets any signed-in user call any route.
