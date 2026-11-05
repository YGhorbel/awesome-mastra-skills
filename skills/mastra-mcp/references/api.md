# MCP API reference

Distilled from `https://mastra.ai/reference/tools/mcp-client.md`, `https://mastra.ai/reference/tools/mcp-server.md`, and `https://mastra.ai/docs/connections/mcp.md`. Package: `@mastra/mcp` (v2, MCP revision `2026-07-28`). Verify against the installed version.

## Contents

- MCPClient constructor
- Server definition (`MastraMCPServerDefinition`)
- MCPClient methods and properties
- OAuth client helpers
- Answering input requests
- Type generation
- MCPServer constructor
- MCPServer methods
- Tool context on the server
- OAuth middleware
- Events (experimental)
- Mastra registry accessors

---

## MCPClient constructor

`new MCPClient<TServers?>({ id?, servers, timeout?, typegen?, clientInfo?, registerProcessHooks?, webhook? })`

| Option | Default | Notes |
|---|---|---|
| `id` | | Required to create several instances with identical configs. |
| `servers` | | `Record<string, MastraMCPServerDefinition>`. The key prefixes tool names. |
| `timeout` | `60000` | ms, all servers unless overridden. |
| `typegen` | | `{ outFile }` for the `generate` CLI. |
| `clientInfo` | key name, `'1.0.0'` | `{ name?, version? }` sent to servers. |
| `registerProcessHooks` | `true` | Installs SIGINT/SIGTERM/SIGHUP/beforeExit hooks that disconnect and exit. |
| `webhook` | | Experimental. Webhook delivery for MCP events. |

---

## Server definition (`MastraMCPServerDefinition`)

`command` means stdio. `url` means Streamable HTTP.

| Field | Transport | Notes |
|---|---|---|
| `command`, `args`, `env` | stdio | |
| `inheritDefaultEnv` | stdio | Default `true` inherits only a curated whitelist (POSIX: `HOME`, `LOGNAME`, `PATH`, `SHELL`, `TERM`, `USER`). `false` passes only `env`. |
| `url` | HTTP | `URL` object. |
| `requestInit` | HTTP | Static headers on every request. |
| `fetch` | HTTP | `(url, init, requestContext) => Response`. `requestContext` is `null` during the handshake. |
| `allowedHosts` | HTTP | Exact host allowlist (`'api.example.com'`, `'localhost:8080'`). Empty array denies all. |
| `authProvider` | HTTP | `OAuthClientProvider`, usually `MCPOAuthClientProvider`. |
| `protocolVersion` | both | `'2026-07-28'` or `'legacy'`. Default probes with `server/discover`. |
| `timeout` | both | Per-server override. |
| `clientInfo` | both | Per-server override. |
| `capabilities` | both | `elicitation` (needs `inputRequests`), `extensions`. |
| `inputRequests` | both | Handler for `input_required` results. |
| `tasks` | both | Experimental. `true` or `{ pollIntervalMs = 5000, maxWaitMs }`. |
| `requireToolApproval` | both | `boolean` or `({ toolName, args, requestContext, annotations }) => boolean \| Promise<boolean>`. |
| `onToolError` | both | `'throw'` (default) raises `MastraError`; `'return'` resolves the full `CallToolResult`. |
| `forwardInstructions` | both | Default `false`. Appends server instructions to the agent system prompt. |
| `instructionsMaxLength` | both | Default `512`. |
| `enableServerLogs` | both | Default `true`. |
| `serverLogLevel` | both | Default `'info'`. |
| `enableProgressTracking` | both | Default `false`. |
| `traceContext` | both | `() => MCPTraceContext \| undefined`. |
| `logger` | both | Extra log handler. |
| `jsonSchemaValidator` | both | For runtimes without dynamic code generation. |

---

## MCPClient methods and properties

| Member | Notes |
|---|---|
| `listTools()` | `Record<string, Tool>`, names `serverName_toolName`. For the `Agent` `tools` option. |
| `listToolsWithErrors({ perServerTimeoutMs }?)` | `{ tools, errors, errorDetails, durations? }`. Keeps working tools when some servers fail. |
| `listToolsets()` | Keys `serverName.toolName`. For `toolsets` in `generate()`/`stream()`. |
| `listToolsetsWithErrors({ perServerTimeoutMs }?)` | `{ toolsets, errors, errorDetails, durations? }` |
| `listToolDefinitions()` / `listToolDefinitionsWithErrors()` / `toolFromDefinition()` / `toolsFromDefinitions()` | Work with raw definitions. |
| `getServerInstructions()` | `Record<string, string \| undefined>` |
| `getServerInfo()` | Announced identity. Untrusted. Not a connectivity check. |
| `authenticate(serverName, { timeoutMs = 5 min }?)` | Interactive loopback OAuth flow. |
| `getServerAuthState(serverName)` | `'needs-auth' \| 'authorized' \| undefined` |
| `cancelAuthentication(serverName)` | `Promise<boolean>` |
| `disconnect()` | Closes all servers. |
| `toMCPServerProxies()` | `Record<string, MCPClientServerProxy>` to spread into `new Mastra({ mcpServers })` (Studio, MCP Apps). |
| `resources` | `list()`, `listWithErrors()`, `templates()`, `templatesWithErrors()`, `read(server, uri)`, `subscribe(server, uri)`, `unsubscribe()`, `onUpdated(server, handler)`, `onListChanged(server, handler)` |
| `prompts` | `list()`, `listWithErrors()`, `get({ serverName, name, args? })`, `onListChanged()` |
| `tools.onListChanged(server, handler)` | |
| `progress.onUpdate(server, handler)` | Needs `enableProgressTracking`. |
| `events` | Experimental: `list(server)`, `subscribe(server, event, args?, options?)`, `handleWebhook(request)`. |
| `tasks` | Experimental: `get`, `update`, `cancel`. |

Tools carry `tool.mcp.annotations` and `tool.title`.

---

## OAuth client helpers

```typescript
import { MCPClient, MCPOAuthClientProvider } from '@mastra/mcp'

const clientMetadataUrl = 'https://app.example.com/oauth/client-metadata.json'

const oauthProvider = new MCPOAuthClientProvider({
  redirectUrl: 'http://127.0.0.1:5533/oauth/callback',
  clientMetadataUrl,
  clientMetadata: {
    client_id: clientMetadataUrl,
    redirect_uris: ['http://127.0.0.1:5533/oauth/callback'],
    client_name: 'My MCP Client',
    grant_types: ['authorization_code', 'refresh_token'],
    response_types: ['code'],
  },
  onRedirectToAuthorization: url => {
    console.log(`Please visit: ${url}`)
  },
})
```

- Configure exactly one identity: `clientInformation` (pre-registered) or `clientMetadataUrl` (CIMD). Both throws. Dynamic Client Registration is not supported.
- One provider per server. Separate `OAuthStorage` namespaces when sharing a persistent backend. Default storage is in memory.
- `createSimpleTokenProvider(token, { redirectUrl, clientMetadata, clientInformation })` for an existing token.
- `createOAuthCallbackServer({ redirectUrl, state })` and `getCallbackUrlCandidates(url)` for host-driven loopback flows. Plain HTTP: local only.

---

## Answering input requests

```typescript
inputRequests: async ({ key, params, signal }) => {
  if (params.mode === 'url') return { action: 'decline' }
  const content = await collectUserInput(params.message, params.requestedSchema, { signal })
  return { action: 'accept', content }
}
```

Return `{ action: 'accept', content }`, `{ action: 'decline' }`, or `{ action: 'cancel' }`. Decline and cancel end the tool call with an error.

---

## Type generation

```typescript
export const mcp = new MCPClient<MCPServers>({
  id: 'weather-client',
  servers: { weather: { url: new URL(process.env.WEATHER_MCP_URL!) } },
  typegen: { outFile: 'src/mcp/mcp-types.generated.ts' },
})
```

Run `npx @mastra/mcp generate ./src/mcp/client.ts`, then typecheck. Importing the client file executes it, so keep it free of startup side effects. Regenerate when server schemas change.

---

## MCPServer constructor

`new MCPServer({...})`

| Option | Notes |
|---|---|
| `id`, `name`, `version` | Required identity. `id` is used by `mastra.getMCPServerById()`. |
| `tools` | `createTool` (or AI SDK) tools. |
| `agents` | Become `ask_<key>` tools with input `{ message }`. Each agent needs a non-empty `description`. |
| `workflows` | Become `run_<key>` tools. Each needs a `description`. Explicit tools win name collisions. |
| `description`, `title`, `websiteUrl`, `icons`, `instructions` | Announced to clients. |
| `resources` | `{ listResources, getResourceContent, resourceTemplates?, resumeSchema? }` |
| `prompts` | `{ listPrompts, getPromptMessages?, resumeSchema? }` |
| `appResources` | `Record<'ui://...', { name, htmlPath \| html, ... }>` for MCP Apps. |
| `mapAuthInfoToUser` | Maps `authInfo` to the FGA user. |
| `fga` | `resourceMapping`, `permissionMapping` for `tools/list` and `tools/call`. |
| `requestState` | `{ key (32+ bytes), ttlSeconds = 600 }` for signed `input_required` continuations. |
| `legacy` | `'reject'` (default) or `'stateless'` to serve 2025-era `initialize` clients (VS Code, Cursor). |
| `toolResult` | `{ modelOutput?: boolean, transform?: (ctx) => CallToolResult \| undefined }` |
| `cacheHints` | Per-operation `ttlMs`/`cacheScope`. |
| `events`, `eventsOptions` | Experimental MCP events. |
| `tasks` | Experimental MCP tasks. |
| `jsonSchemaValidator`, `repository`, `releaseDate`, `isLatest`, `packageCanonical`, `packages`, `remotes` | Metadata and runtime options. |

A tool with `outputSchema` returns `structuredContent`, validated before sending.

---

## MCPServer methods

| Method | Notes |
|---|---|
| `startStdio()` | Serve over stdin/stdout. |
| `startHTTP({ url, httpPath, req, res, options? })` | Node `IncomingMessage`/`ServerResponse`. Stateless per request. `options`: `enableDnsRebindingProtection`, `allowedHosts`, `allowedOrigins`. |
| `close()` | Release resources. |
| `getServerInfo()`, `getServerDetail()`, `getToolListInfo()`, `getToolInfo(id)` | Introspection. |
| `executeTool(toolId, args, { requestContext, resumeData, suspendPayload }?)` | Returns `{ status: 'completed', output }` or `{ status: 'suspended', suspendPayload, resumeSchema }`. |
| `tools()` | Registered tool registry. |
| `toolActions.add(tools)`, `toolActions.remove(ids)`, `toolActions.notifyListChanged()` | Dynamic tools; also sync the Mastra tool registry. |
| `resources.notifyUpdated({ uri })`, `resources.notifyListChanged()`, `prompts.notifyListChanged()` | Delivered on the client's `subscriptions/listen` stream. |
| `events.emit(name, data, options?)` | Experimental. |

---

## Tool context on the server

| Member | Notes |
|---|---|
| `context.mcp.extra.signal` | Aborts on client cancel. |
| `context.mcp.extra.requestId` | JSON-RPC id. |
| `context.mcp.extra.authInfo` | Whatever middleware set on `req.auth`. Set `extra.sub` for the user id. |
| `context.mcp.extra._meta` | Trace, log level, progress token. |
| `context.mcp.log()`, `context.mcp.progress()` | Notifications to the caller. |
| `context.requestContext` | Carries `authInfo`, mapped `user`, `traceContext`. Also present for tools reached via `ask_<agent>`. |
| `context.suspend(payload)`, `context.resumeData` | `input_required` rounds; needs `resumeSchema` (flat object of primitives). |

Read auth both ways: `context.mcp?.extra.authInfo ?? context.requestContext?.get('authInfo')`.

---

## OAuth middleware

```typescript
import { createOAuthMiddleware, createIntrospectionValidator } from '@mastra/mcp'

const oauthMiddleware = createOAuthMiddleware({
  oauth: {
    resource: 'https://mcp.example.com/mcp',
    authorizationServers: ['https://auth.example.com'],
    scopesSupported: ['mcp:read', 'mcp:write'],
    resourceName: 'My Protected MCP Server',
    validateToken: createIntrospectionValidator('https://auth.example.com/oauth/introspect', {
      clientId: 'mcp-server',
      clientSecret: process.env.MCP_INTROSPECTION_SECRET!,
    }),
  },
  mcpPath: '/mcp',
})
```

| Option | Default | Notes |
|---|---|---|
| `oauth.resource` | | Canonical server URL, returned in Protected Resource Metadata. |
| `oauth.authorizationServers` | | Issuer URLs. |
| `oauth.scopesSupported` | `['mcp:read', 'mcp:write']` | |
| `oauth.resourceName` | | |
| `oauth.validateToken` | none | Without it, tokens are accepted unvalidated. Return `{ valid, scopes, subject }` or `{ valid: false, error }`. |
| `mcpPath` | `'/mcp'` | Only this path requires auth. |

Serves `/.well-known/oauth-protected-resource`, returns `401` with `WWW-Authenticate`. Usage: `const result = await oauthMiddleware(req, res, url); if (!result.proceed) return`. Validators: `createStaticTokenValidator([...])` (testing), `createIntrospectionValidator(url, creds)`, or a custom function.

---

## Events (experimental)

Server: `events: { 'ticket.created': defineEvent({ description, inputSchema, payloadSchema, match, authorize, poll?, delivery?, bufferSize = 1000, pollIntervalMs }) }`, publish with `server.events.emit(name, data)`. `eventsOptions`: `heartbeatIntervalMs` (30000), `listPageSize` (100), `maxStreams` (1024), `webhook`.

Client: `await mcp.events.list(server)`, `const sub = await mcp.events.subscribe(server, name, args, { cursor, delivery, maxAgeMs, maxEvents, minPollIntervalMs = 1000, heartbeatTimeoutMs = 60000 })`, then `for await (const event of sub)`. Save `sub.cursor` after handling. Delivery is at least once; dedupe by `eventId`. `emit()` buffers in one process only.

---

## Mastra registry accessors

`mastra.getMCPServer(key)`, `mastra.getMCPServerById(id)`, `mastra.listMCPServers()`. Registered servers are served at `/api/mcp/:serverId/mcp`, with Studio REST routes under `/api/mcp/*`.
