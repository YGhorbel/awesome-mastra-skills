# MCP examples

All examples follow the current docs at `https://mastra.ai/docs/connections/mcp` and the `MCPClient` and `MCPServer` references. Verify against the installed `@mastra/mcp` before copying.

## Contents

1. Agent with static MCP tools and approval
2. Per-user credentials: runtime toolsets and forwarded headers
3. Expose Mastra tools and agents, over Mastra's server and as a stdio package
4. Custom HTTP server protected with OAuth, with identity in tools

---

## 1. Agent with static MCP tools and approval

```typescript
// src/mastra/mcp/client.ts
import { MCPClient } from '@mastra/mcp'

export const mcpClient = new MCPClient({
  id: 'assistant-mcp',
  servers: {
    wikipedia: {
      command: 'npx',
      args: ['-y', 'wikipedia-mcp'],
    },
    github: {
      url: new URL('https://github.example.com/mcp'),
      requestInit: {
        headers: { Authorization: `Bearer ${process.env.GITHUB_MCP_TOKEN}` },
      },
      requireToolApproval: ({ toolName }) => toolName.startsWith('delete_'),
    },
  },
})
```

```typescript
// src/mastra/agents/assistant.ts
import { Agent } from '@mastra/core/agent'
import { mcpClient } from '../mcp/client'

// Keep working tools even if one server is down
const { tools, errors } = await mcpClient.listToolsWithErrors({ perServerTimeoutMs: 3_000 })
if (Object.keys(errors).length) console.warn('MCP servers unavailable', errors)

export const assistant = new Agent({
  id: 'assistant',
  name: 'Assistant',
  description: 'Answers questions using Wikipedia and GitHub.',
  instructions: `
    Use the available MCP tools to answer questions.
    Include the source of any information you retrieve.
  `,
  model: 'openai/gpt-6.1-sol',
  tools,
})
```

Calls to `github_delete_*` tools suspend for approval. Resume them as described in `mastra-agent-approval-hitl`.

---

## 2. Per-user credentials: runtime toolsets and forwarded headers

Option A, a client per request (each user's own API key):

```typescript
import { MCPClient } from '@mastra/mcp'
import { mastra } from './mastra'

export async function handleRequest(prompt: string, apiKey: string) {
  const userMcpClient = new MCPClient({
    servers: {
      weather: {
        url: new URL('https://weather.example.com/mcp'),
        requestInit: {
          headers: { Authorization: `Bearer ${apiKey}` },
        },
      },
    },
  })

  try {
    const agent = mastra.getAgent('assistant')
    const response = await agent.generate(prompt, {
      toolsets: await userMcpClient.listToolsets(),
    })
    return response.text
  } finally {
    await userMcpClient.disconnect()
  }
}
```

Option B, one static client that forwards a request-scoped credential:

```typescript
import { MCPClient } from '@mastra/mcp'

export const mcpClient = new MCPClient({
  id: 'api-mcp',
  servers: {
    apiServer: {
      url: new URL('https://api.example.com/mcp'),
      allowedHosts: ['api.example.com'],
      fetch: async (url, init, requestContext) => {
        const headers = new Headers(init?.headers)
        const cookie = requestContext?.get('cookie')
        if (cookie) headers.set('cookie', cookie)
        return fetch(url, { ...init, headers })
      },
    },
  },
})
```

Pass `requestContext` to `agent.generate(..., { requestContext })`; it is forwarded to the custom `fetch`. Populate it from authenticated middleware (see `mastra-server`).

---

## 3. Expose Mastra tools and agents, over Mastra's server and as a stdio package

```typescript
// src/mastra/mcp/server.ts
import { MCPServer } from '@mastra/mcp'
import { assistant } from '../agents/assistant'
import { weatherTool } from '../tools/weather'
import { weatherWorkflow } from '../workflows/weather'

export const mcpServer = new MCPServer({
  id: 'my-mcp-server',
  name: 'My MCP Server',
  version: '1.0.0',
  description: 'Weather data and an assistant agent',
  agents: { assistant },          // exposed as ask_assistant
  tools: { weatherTool },
  workflows: { weatherWorkflow }, // exposed as run_weatherWorkflow
  legacy: 'stateless',            // accept 2025-era clients such as Cursor and VS Code
})
```

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core/mastra'
import { mcpServer } from './mcp/server'

export const mastra = new Mastra({
  mcpServers: { mcpServer },
})
```

Clients connect to `https://<host>/api/mcp/my-mcp-server/mcp`. Protect it with `server.auth` (see `mastra-auth`).

To also ship it as a local stdio command:

```typescript
#!/usr/bin/env node
// src/stdio.ts
import { mcpServer } from './mastra/mcp/server'

mcpServer.startStdio().catch(error => {
  console.error('Failed to start MCP server:', error)
  process.exit(1)
})
```

```json
{
  "bin": { "my-mcp-server": "dist/stdio.js" },
  "files": ["dist"]
}
```

Consumers then configure `{ command: 'npx', args: ['-y', '@your-org/my-mcp-server@1.0.0'] }`.

---

## 4. Custom HTTP server protected with OAuth, with identity in tools

```typescript
import http from 'node:http'
import { createTool } from '@mastra/core/tools'
import { MCPServer, createOAuthMiddleware, createIntrospectionValidator } from '@mastra/mcp'
import { z } from 'zod'

const listInvoices = createTool({
  id: 'listInvoices',
  description: 'Lists invoices for the signed-in user',
  inputSchema: z.object({}),
  execute: async (_input, context) => {
    const authInfo = context.mcp?.extra.authInfo ?? context.requestContext?.get('authInfo')
    const userId = authInfo?.extra?.sub
    if (!userId) return { error: 'Authentication required' }
    // Resolve the tenant from trusted auth data, never from tool arguments.
    // Use a credential meant for the upstream API, not the MCP token.
    return { invoices: await loadInvoicesForUser(userId as string) }
  },
})

const mcpServer = new MCPServer({
  id: 'billing',
  name: 'Billing',
  version: '1.0.0',
  tools: { listInvoices },
  requestState: { key: process.env.MCP_REQUEST_STATE_KEY!, ttlSeconds: 600 },
})

const oauthMiddleware = createOAuthMiddleware({
  oauth: {
    resource: 'https://mcp.example.com/mcp',
    authorizationServers: ['https://auth.example.com'],
    validateToken: createIntrospectionValidator('https://auth.example.com/oauth/introspect', {
      clientId: 'mcp-server',
      clientSecret: process.env.MCP_INTROSPECTION_SECRET!,
    }),
  },
  mcpPath: '/mcp',
})

const httpServer = http.createServer(async (req, res) => {
  const url = new URL(req.url || '', 'https://mcp.example.com')
  const result = await oauthMiddleware(req, res, url)
  if (!result.proceed) return
  await mcpServer.startHTTP({ url, httpPath: '/mcp', req, res })
})

httpServer.listen(3000)
```

`loadInvoicesForUser` is your own data access function. The middleware serves Protected Resource Metadata and returns `401` without a valid token. Return `subject` from custom validators so `input_required` continuations bind to the user.
