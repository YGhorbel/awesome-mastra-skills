---
name: mastra-mcp
description: "Connect Mastra agents to Model Context Protocol servers with MCPClient, and expose Mastra tools, agents, workflows, resources, and prompts to other MCP clients with MCPServer, including stdio and Streamable HTTP transports, static vs runtime toolsets, per-user credentials, OAuth on both sides, tool approval, and MCP Apps. Use this skill whenever the user wants an agent to use an MCP server (GitHub, Wikipedia, a registry like Smithery or Composio), pass different API keys per user to MCP tools, publish their Mastra tools to Cursor, Claude Desktop, or VS Code, ship an npx stdio MCP server, or protect an MCP endpoint with OAuth. Triggers on MCP, Model Context Protocol, @mastra/mcp, MCPClient, MCPServer, listTools, listToolsets, toolsets, mcpServers, startStdio, startHTTP, MCPOAuthClientProvider, createOAuthMiddleware, requireToolApproval, inputRequests, appResources, MCP events, mcp-types.generated. Also triggers when the user mentions an MCP config file or a server URL ending in /mcp."
license: Apache-2.0
metadata:
  category: connections
  catalog_summary: "MCPClient and MCPServer: transports, static vs runtime toolsets, per-user auth, OAuth, approval, publishing MCP servers"
  display_order: 1
  docs: https://mastra.ai/docs/connections/mcp
---

# Mastra MCP

Consume MCP servers as agent tools with `MCPClient`, and publish Mastra capabilities to external MCP clients with `MCPServer`, with credentials and permissions scoped correctly.

---

## When to use

- Giving an agent tools from a local (`command`) or remote (`url`) MCP server
- Choosing static tools (`listTools()`) vs per-request toolsets (`listToolsets()`)
- Sending per-user API keys or forwarding request credentials to MCP servers
- Connecting to an OAuth-protected MCP server
- Requiring approval for some or all MCP tools
- Exposing Mastra tools, agents (`ask_<key>`), and workflows (`run_<key>`) as an MCP server
- Serving over Mastra's server, a custom HTTP server, serverless, or stdio (`npx` package)
- Protecting an MCP server with OAuth and passing caller identity to tools
- MCP Apps (`ui://` resources) and experimental MCP events

## When NOT to use

- Writing ordinary tools with `createTool` (use `mastra-tools`)
- Managed OAuth for hosted MCP servers through Mastra Connect (use `mastra-tool-integrations`)
- Remote agents over A2A, ACP coding agents, or SDK agents (use `mastra-a2a-acp`)
- Approval UI and resuming suspended runs in general (use `mastra-agent-approval-hitl`)
- Mastra server auth, middleware, and route protection (use `mastra-server` and `mastra-auth`)
- Upgrading from `@mastra/mcp` 1.x (use `mastra-migrations`)

---

## Required inputs

- Direction: consume (client), expose (server), or both
- For each server to consume: transport (`command` + `args`, or `url`), and credentials
- Whose credentials: one shared service account, or each user's own
- Trust in each server (drives `requireToolApproval`, `forwardInstructions`, `allowedHosts`)
- For a server you expose: which tools, agents, workflows; transport; who may call it

---

## The framework: client and server

Both classes come from `@mastra/mcp` and speak MCP revision `2026-07-28` over stdio and Streamable HTTP.

### Client: connect and pass tools to an agent

```typescript
import { MCPClient } from '@mastra/mcp'

export const mcpClient = new MCPClient({
  id: 'my-mcp-client',
  servers: {
    wikipedia: {
      command: 'npx',
      args: ['-y', 'wikipedia-mcp'],
    },
    weather: {
      url: new URL('https://weather.example.com/mcp'),
      requestInit: {
        headers: { Authorization: `Bearer ${process.env.WEATHER_API_KEY}` },
      },
    },
  },
})
```

```typescript
import { Agent } from '@mastra/core/agent'
import { mcpClient } from '../mcp/client'

export const assistant = new Agent({
  id: 'assistant',
  name: 'Assistant',
  instructions: 'Use the available MCP tools to answer questions. Include the source of any information you retrieve.',
  model: 'openai/gpt-6.1-sol',
  tools: await mcpClient.listTools(),
})
```

`command` selects stdio. `url` selects Streamable HTTP. `listTools()` names tools `serverName_toolName`.

### Static tools vs runtime toolsets

| | Static tools | Runtime toolsets |
|---|---|---|
| Method | `await mcpClient.listTools()` | `await mcpClient.listToolsets()` |
| Use case | Shared, fixed configuration | Per-user or per-request configuration |
| Credentials | Shared by all requests | Vary per request |
| Agent API | `tools` in the `Agent` constructor | `toolsets` in `generate()` or `stream()` |

### Server: expose Mastra primitives

```typescript
import { MCPServer } from '@mastra/mcp'
import { assistant } from '../agents/assistant'
import { weatherTool } from '../tools/weather'
import { weatherWorkflow } from '../workflows/weather'

export const mcpServer = new MCPServer({
  id: 'my-mcp-server',
  name: 'My MCP Server',
  version: '1.0.0',
  agents: { assistant },       // tool "ask_assistant", agent needs a description
  tools: { weatherTool },
  workflows: { weatherWorkflow }, // tool "run_weatherWorkflow", workflow needs a description
})
```

Register it with `new Mastra({ mcpServers: { mcpServer } })`. Mastra serves it at `/api/mcp/:serverId/mcp` over Streamable HTTP, which also works on serverless.

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/mcp/dist/docs/` and the installed `MCPClient` and `MCPServer` types. Otherwise fetch `https://mastra.ai/docs/connections/mcp.md`, `https://mastra.ai/reference/tools/mcp-client.md`, and `https://mastra.ai/reference/tools/mcp-server.md`. Trust these over memory.
2. **Install** `npm install @mastra/mcp@latest`.
3. **Client side:** define servers once at module scope with a stable `id`. Secrets come from env vars, never literals.
4. **Pick the loading mode.** Shared credentials: `listTools()` on the agent. Per-user credentials: build a client per request, pass `listToolsets()` as `toolsets`, then `disconnect()`.
5. **Set trust controls.** `requireToolApproval` (boolean or function), `allowedHosts` for URLs from untrusted config, `inheritDefaultEnv: false` for stdio servers that should see only `env`. Leave `forwardInstructions` off for third-party servers.
6. **OAuth servers:** one `MCPOAuthClientProvider` per server with either `clientInformation` or `clientMetadataUrl`. Handle `'needs-auth'` with `authenticate()` in local tools; hosted apps own their callback route.
7. **Server side:** give every exposed agent and workflow a `description`. Register on `Mastra`, or call `startHTTP()` / `startStdio()` yourself.
8. **Protect the server.** Use `createOAuthMiddleware` with a real `validateToken`, protect `/api/mcp/*` REST routes with `server.auth`, and authorize records inside tools from trusted context.
9. **Test.** In Studio, open the agent and the MCP server pages. For servers, connect from an MCP client such as Cursor. Set `legacy: 'stateless'` if 2025-era clients must connect.

---

## Deep dive: per-user credentials

Static `listTools()` bakes one credential into every call. For per-user keys, create a client per request:

```typescript
import { MCPClient } from '@mastra/mcp'
import { mastra } from './mastra'

export async function handleRequest(prompt: string, apiKey: string) {
  const userMcpClient = new MCPClient({
    servers: {
      weather: {
        url: new URL('https://weather.example.com/mcp'),
        requestInit: { headers: { Authorization: `Bearer ${apiKey}` } },
      },
    },
  })

  const agent = mastra.getAgent('assistant')
  const response = await agent.generate(prompt, {
    toolsets: await userMcpClient.listToolsets(),
  })
  await userMcpClient.disconnect()
  return response.text
}
```

Alternative: keep one static client and supply a custom `fetch(url, init, requestContext)` that adds headers from `requestContext`. `requestContext` is `null` during the initial handshake, so do not throw when it is missing; forward the request and let the server reject it.

For a server you expose, never pass the incoming MCP access token to upstream APIs. Look up a separate credential for the authenticated user.

---

## Failure patterns

- **`MCPClient` created per request without an `id` or `disconnect()`.** Identical configs throw to prevent leaks. Give each instance a unique `id`, or `await client.disconnect()` before recreating.
- **Per-user keys in `listTools()` on a shared agent.** Every user shares one credential. Use `listToolsets()` per request or a custom `fetch`.
- **Agent or workflow without `description` in `MCPServer`.** Server construction throws. Add a non-empty description.
- **Expecting tool names to match the server's.** Client tools are `server_tool` (`listTools`) or `server.tool` (`listToolsets`). Server-side agents become `ask_<key>`, workflows `run_<key>`.
- **Cursor or VS Code cannot connect over HTTP.** `MCPServer` rejects 2025-era `initialize` clients by default. Set `legacy: 'stateless'`.
- **`createOAuthMiddleware` without `validateToken`.** Tokens are accepted unvalidated. Use `createIntrospectionValidator` or a JWT check with audience and expiry.
- **Only protecting `/mcp`.** Mastra also registers REST routes under `/api/mcp/*` (including tool execute). Use `server.auth` or default-deny them.
- **Trusting tool annotations from third-party servers.** `readOnlyHint` is advisory. Only relax approval for trusted servers.
- **`forwardInstructions: true` on an untrusted server.** Its instructions enter the system prompt verbatim. Inspect with `getServerInstructions()` first.
- **One `MCPOAuthClientProvider` shared across servers.** Flows overwrite each other. Use one per server and namespaced storage.
- **Process exits during graceful shutdown.** The client installs signal hooks by default. Set `registerProcessHooks: false` and call `disconnect()` yourself.
- **`input_required` errors from a server.** Configure `inputRequests` on that server definition.
- **Continuations failing across instances.** Set `requestState.key` (32+ bytes from env) on `MCPServer` so every instance shares it.

---

## Output format

A finished MCP delivery contains:

- `src/mastra/mcp/client.ts` exporting a configured `MCPClient`, and/or `src/mastra/mcp/server.ts` exporting an `MCPServer`
- Agent wiring (`tools: await mcpClient.listTools()`) or a request handler using `toolsets`
- Server registration in `new Mastra({ mcpServers })`, or a stdio entry file with `bin` in `package.json`
- Env vars in `.env.example` (server URLs, API keys, OAuth client settings, `MCP_REQUEST_STATE_KEY`)
- Approval, `allowedHosts`, and auth configuration matching the trust level
- Evidence: tools listed in Studio, or a successful call from an external MCP client

---

## Reference files

- [`references/api.md`](references/api.md) - `MCPClient` options, server definition fields, methods; `MCPServer` options, methods, OAuth middleware, context.
- [`references/examples.md`](references/examples.md) - Static client agent with approval, per-user toolsets and forwarded headers, exposed server plus stdio package, OAuth-protected HTTP server.
- [`references/checklist.md`](references/checklist.md) - Client, server, and auth production checklist.

**Live docs**

- https://mastra.ai/docs/connections/mcp
- https://mastra.ai/reference/tools/mcp-client
- https://mastra.ai/reference/tools/mcp-server
- https://mastra.ai/docs/guides/mcp-authentication-authorization
- https://mastra.ai/reference/migrations/mcp-v2
