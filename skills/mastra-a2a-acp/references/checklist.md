# A2A, ACP, and SDK agents checklist

Run this before calling a connection done.

## Choice

- [ ] Connection type matches runtime ownership: remote service (A2A), local coding-agent process (ACP), vendor SDK (SDK agents), tools only (MCP, see `mastra-mcp`)
- [ ] Every wrapped agent has a clear `description` so the parent model knows when to delegate

## A2A

- [ ] Full agent card URL used for multi-agent servers
- [ ] `protocolVersion` matches the remote (`'1.0'` or default v0.3)
- [ ] Auth headers from env vars; timeouts and retries set
- [ ] `verifyAgentCard` enforces the expected provider or endpoint; signed cards verified where required
- [ ] Exposing server has storage so suspended runs can resume
- [ ] HITL flows routed to the same instance (task records are in memory) or deployed as a single instance
- [ ] Push notification callbacks validate the `token`, avoid internal targets, and are re-registered after restarts
- [ ] Server routes protected by server auth (see `mastra-auth`)

## ACP

- [ ] Coding agent installed and its current ACP flag confirmed in its own docs
- [ ] `onPermissionRequest` defined (the default auto-selects the first option)
- [ ] `cwd` is a disposable checkout or the process runs in a container for untrusted tasks
- [ ] `workspace` set when ACP file requests must go through a specific filesystem
- [ ] `persistSession` chosen deliberately (reuse context vs isolate each prompt)
- [ ] `createClient` extends the client if the agent calls extension methods
- [ ] No code path calls `resumeGenerate()` / `resumeStream()` on `AcpAgent`

## SDK agents

- [ ] Mastra package and peer SDK installed; vendor key in `.env.example`
- [ ] Tools configured through the vendor SDK (`mcpServers`, `allowedTools`, `sdkOptions.tools`), not Mastra `tools`
- [ ] Cursor local agents set `sdkOptions.model`; no `structuredOutput` on Cursor
- [ ] Agents registered on `Mastra` and fetched with `getAgentById()`

## Verification

- [ ] A Studio run shows the parent delegating and receiving a result
- [ ] Traces show the subagent span with usage (see `mastra-observability`)
- [ ] A failure path (remote down, permission denied) returns a clear error to the user
