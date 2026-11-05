# MCP checklist

Run this before calling an MCP integration done. The server and auth items follow the production checklist in `https://mastra.ai/docs/guides/mcp-authentication-authorization`.

## Client

- [ ] `@mastra/mcp` is v2 (MCP `2026-07-28`); old v1 code migrated (see `mastra-migrations`)
- [ ] Each `MCPClient` defined once at module scope with a stable `id`, or created per request and disconnected in `finally`
- [ ] Shared credentials use `listTools()`; per-user credentials use `listToolsets()` or a custom `fetch`
- [ ] Secrets come from env vars and are listed in `.env.example`
- [ ] Stdio servers get only the variables they need (`env`, `inheritDefaultEnv: false` for strict isolation)
- [ ] `allowedHosts` set on any server whose URL comes from user or untrusted config
- [ ] `requireToolApproval` covers destructive tools; annotations used only for trusted servers
- [ ] `forwardInstructions` off for third-party servers
- [ ] Tool output treated as untrusted; guardrail processors considered (see `mastra-processors-guardrails`)
- [ ] `listToolsWithErrors` or error handling so one failing server does not break the agent
- [ ] Shutdown handled: default hooks, or `registerProcessHooks: false` plus `disconnect()` in your handler

## OAuth client

- [ ] One `MCPOAuthClientProvider` per server, with exactly one of `clientInformation` or `clientMetadataUrl`
- [ ] The authorization server supports the chosen registration mechanism (CIMD or pre-registration)
- [ ] Token storage persisted with an `OAuthStorage` scoped per user and connection, not the default in-memory store
- [ ] Hosted apps own their HTTPS callback endpoint; loopback `authenticate()` used only for local tools

## Server

- [ ] Every exposed agent and workflow has a `description`
- [ ] Registered in `new Mastra({ mcpServers })`, or `startHTTP` / `startStdio` wired explicitly
- [ ] `legacy: 'stateless'` set if 2025-era clients must connect
- [ ] `requestState.key` shared across instances when tools suspend for input
- [ ] `startHTTP` DNS rebinding protection (`allowedHosts`, `allowedOrigins`) for browser-reachable local servers

## Server auth

- [ ] Tokens validated (issuer, audience, expiry); an unvalidated token is rejected
- [ ] Every protected path returns `401` without a bearer token
- [ ] `/api/mcp/:serverId/tools*`, `/api/mcp/:serverId/resources*`, `/api/mcp/v0/servers*` not reachable without auth
- [ ] Unauthorized callers denied on `tools/call` and the REST execute route, including unlisted tools
- [ ] Records scoped to the caller from trusted context, not tool arguments
- [ ] Resources, prompts, and event subscriptions authorized in application code (`authorize` on events)
- [ ] Upstream APIs called with separate credentials; the MCP token is never forwarded
- [ ] Tokens and credentials kept out of instructions, tool arguments, and tool results
