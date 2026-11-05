# Studio and Editor examples

All examples follow the current docs. Verify against the installed version before copying.

## Contents

1. Team Studio with Simple Auth and RBAC
2. Serve Studio alongside the server
3. Editor with database storage and tool providers
4. Editor overrides as repository files
5. Prompt block with a request-context fallback
6. Testing a draft sub-agent

---

## 1. Team Studio with Simple Auth and RBAC

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { SimpleAuth } from '@mastra/core/server'
import { StaticRBACProvider, DEFAULT_ROLES } from '@mastra/core/auth/ee'

export const mastra = new Mastra({
  server: {
    auth: new SimpleAuth({
      tokens: {
        'admin-key': { id: 'user-1', name: 'Alice', role: 'admin' },
        'viewer-key': { id: 'user-2', name: 'Bob', role: 'viewer' },
      },
    }),
    rbac: new StaticRBACProvider({
      roles: DEFAULT_ROLES,
      getUserRoles: user => [user.role],
    }),
  },
})
```

Studio now shows a login screen and hides actions a role lacks. Keep tokens in env vars in real code. RBAC in production needs an EE license. For an identity provider with its own roles, use `roleMapping`:

```typescript
const rbac = new StaticRBACProvider({
  roleMapping: {
    'org:admin': ['*'],
    'org:member': ['*:read', '*:execute'],
    'org:viewer': ['*:read'],
  },
  getUserRoles: user => user.providerRoles,
})
```

---

## 2. Serve Studio alongside the server

```bash
npx mastra build --studio
MASTRA_STUDIO_PATH=.mastra/output/studio node .mastra/output/index.mjs
```

Standalone instead, under a subpath behind a proxy:

```bash
npm install -g mastra
MASTRA_STUDIO_BASE_PATH=/agents mastra studio
```

---

## 3. Editor with database storage and tool providers

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { MastraCompositeStore } from '@mastra/core/storage'
import { MastraEditor } from '@mastra/editor'
import { ComposioToolProvider } from '@mastra/editor/composio'
import { ArcadeToolProvider } from '@mastra/editor/arcade'
import { LibSQLStore } from '@mastra/libsql'
import { supportAgent } from './agents/support-agent'
import { searchOrders } from './tools/search-orders'

export const mastra = new Mastra({
  agents: { supportAgent },
  tools: { searchOrders }, // pickable in the Studio tool picker
  storage: new MastraCompositeStore({
    id: 'mastra-storage',
    default: new LibSQLStore({ id: 'app-storage', url: 'file:./mastra.db' }),
    editor: new LibSQLStore({ id: 'editor-storage', url: 'file:./editor.db' }),
  }),
  editor: new MastraEditor({
    toolProviders: {
      composio: new ComposioToolProvider({ apiKey: process.env.COMPOSIO_API_KEY! }),
      arcade: new ArcadeToolProvider({ apiKey: process.env.ARCADE_API_KEY! }),
    },
  }),
})
```

```typescript
// src/mastra/agents/support-agent.ts
import { Agent } from '@mastra/core/agent'
import { searchOrders } from '../tools/search-orders'

export const supportAgent = new Agent({
  id: 'support-agent',
  name: 'Support agent',
  model: 'openai/gpt-6.1-sol',
  tools: { searchOrders },
  editor: {
    instructions: true,
    tools: { description: true },
  },
})
```

Publish a first version with instructions in Studio (Agents, Support agent, Editor) before the agent can run.

---

## 4. Editor overrides as repository files

```typescript
import { Mastra } from '@mastra/core'
import { MastraEditor } from '@mastra/editor'

export const mastra = new Mastra({
  agents: {/* existing agents */},
  editor: new MastraEditor({ source: 'code', codePath: './mastra/editor' }),
})
```

Saving `support-agent` in Studio writes `mastra/editor/agents/support-agent.json`:

```json
{
  "instructions": "Help customers with Acme products and answer in their language.",
  "tools": {
    "searchOrders": { "description": "Look up an order by its number" }
  }
}
```

Review it in a pull request. Git history becomes the version history.

---

## 5. Prompt block with a request-context fallback

```typescript
import { mastra } from '../src/mastra'

const editor = mastra.getEditor()!

await editor.prompt.create({
  id: 'default-user-prompt',
  name: 'Default user prompt',
  content: 'Help the user with their Acme account.',
})

await editor.agent.update({
  id: 'support-agent',
  instructions: [
    { type: 'text', content: 'Follow the platform safety policy.' },
    {
      type: 'prompt_block',
      content: '{{userPrompt}}',
      rules: {
        operator: 'AND',
        conditions: [
          { field: 'userPrompt', operator: 'exists' },
          { field: 'userPrompt', operator: 'not_equals', value: '' },
        ],
      },
    },
    {
      type: 'prompt_block_ref',
      id: 'default-user-prompt',
      rules: {
        operator: 'OR',
        conditions: [
          { field: 'userPrompt', operator: 'not_exists' },
          { field: 'userPrompt', operator: 'equals', value: '' },
        ],
      },
    },
  ],
})
```

Both calls create drafts. Publish the block and the agent version in Studio, or set `status: 'published'` with the `activeVersionId` from the Client SDK `listVersions()`.

---

## 6. Testing a draft sub-agent

```typescript
import { Mastra } from '@mastra/core'
import { MastraEditor } from '@mastra/editor'

export const mastra = new Mastra({
  agents: { supervisor, researchAgent, writerAgent },
  editor: new MastraEditor(),
  versions: {
    agents: {
      'research-agent': { status: 'published' },
      'writer-agent': { versionId: 'abc-123' },
    },
  },
})

// Override one sub-agent for this call only
const result = await mastra.getAgentById('supervisor').generate('Research and write about AI safety', {
  versions: { agents: { 'research-agent': { status: 'draft' } } },
})
```

If a version cannot be resolved, Mastra logs a warning and uses the code-defined sub-agent.
