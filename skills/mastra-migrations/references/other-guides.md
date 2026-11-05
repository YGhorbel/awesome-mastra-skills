# Other migration guides

Distilled from `https://mastra.ai/reference/migrations/{vnext-to-standard-apis,ai-sdk-v4-to-v5,agentnetwork,network-to-supervisor,mcp-v2,mastra-cloud}`. Some of these predate v1; where a guide conflicts with v1, follow v1.

## Contents

- VNext to standard APIs (0.20)
- AI SDK v4 to v5
- AgentNetwork to `.network()` (0.20)
- `.network()` to supervisor agents
- `@mastra/mcp` v1 to v2
- Mastra Cloud to Mastra Platform

---

## VNext to standard APIs (0.20)

As of `@mastra/core` 0.20:

| Old | New | Models |
|---|---|---|
| `.stream()`, `.generate()` | `.streamLegacy()`, `.generateLegacy()` | AI SDK v4 (`specificationVersion: 'v1'`) |
| `.streamVNext()`, `.generateVNext()` | `.stream()`, `.generate()` | AI SDK v5 (`specificationVersion: 'v2'`) |

Paths: keep v4 models (rename to `*Legacy`), keep v5 models (rename `*VNext` to standard), or upgrade v4 to v5 (bump every provider package one major). The runtime enforces the model version. This guide shows a `format: 'aisdk'` option; v1 removed `format`, so do not add it in new code.

## AI SDK v4 to v5

- Follow the AI SDK v5 migration guide for AI SDK changes. Mastra-specific parts only here.
- No database migration. `MessageList` converts stored v4 messages on the fly. Data written in v5 format does not work after a downgrade, so keep backups.
- Manual conversion:

```typescript
import { convertMessages } from '@mastra/core/agent'

// Convert AI SDK v4 messages to v5
const aiv5Messages = convertMessages(aiv4Messages).to('AIV5.UI')

// Convert Mastra messages to AI SDK v5
const aiv5ModelMessages = convertMessages(mastraMessages).to('AIV5.Model')
// Supported output formats:
// 'Mastra.V2', 'AIV4.UI', 'AIV4.Core', 'AIV5.UI', 'AIV5.Model', 'AIV6.UI'
```

- Tool type helpers: `InferUITool` and `InferUITools` from `@mastra/core/tools`.

## AgentNetwork to `.network()` (0.20)

Replace `new AgentNetwork({...})` from `@mastra/core/network` with `new Agent({...})` that has `agents`, `tools`, and a `Memory`. Memory is required. This path is itself deprecated now; go straight to supervisor agents.

## `.network()` to supervisor agents

`.network()` is deprecated and will be removed. Keep the agent configuration (`agents`, `workflows`, `tools`, `memory`) and change the call:

```typescript
const stream = await supervisorAgent.stream('Research AI in education', {
  maxSteps: 10,
})

for await (const chunk of stream.textStream) {
  process.stdout.write(chunk)
}
```

```typescript
const result = await supervisorAgent.generate('Research AI in education', {
  maxSteps: 10,
})
console.log(result.text)
```

Steps in the guide:

1. Replace `.network()` with `.stream()` or `.generate()`; `maxSteps` replaces the implicit iteration limit.
2. Rewrite instructions to list available resources, when to use each, how to coordinate, and when the task is complete.
3. Add a `description` to every subagent.
4. Replace `network-execution-event-*` handling with `textStream` or `fullStream`.
5. Optionally add `delegation` hooks (`onDelegationStart`, `onDelegationComplete`), message filtering, iteration monitoring (`onIterationComplete`), and task completion scoring (`isTaskComplete`).

See `mastra-multi-agent` for the full supervisor API.

## `@mastra/mcp` v1 to v2

- v2 serves only MCP revision 2026-07-28. No `initialize` handshake, no session header, no standalone `GET /sse` + `POST /messages` transport. Streamable HTTP still uses SSE framing.
- The v2 client probes servers and speaks whichever revision each offers.
- Stay on 1.x if you must serve pre-2026 clients. A Mastra instance can register 1.x and 2.x servers side by side.
- Requires `@mastra/core` 1.76 or later:

```diff
- "@mastra/core": "^1.60.0",
- "@mastra/mcp": "^1.17.0"
+ "@mastra/core": "^1.76.0",
+ "@mastra/mcp": "^2.0.0"
```

- `context.mcp.elicitation.sendRequest()` becomes `context.suspend(payload)` with `suspendSchema` and `resumeSchema`; the tool reruns with `context.resumeData` and `context.suspendPayload`. Each round sees only the previous payload and the current answer.
- `executeTool` reports a suspension; resource and prompt callbacks can suspend.
- Per-request logging replaces session log levels; client input handlers are configured per server; client `protocolVersion` pins a revision; OAuth clients are pre-registered or use a Client ID Metadata Document.
- Removed: server `protocolVersion`, `startSSE`, `startHonoSSE`, `connectSSE`, `handleServerlessRequest`, `sessionId`, `sessionIds`, `reconnectionOptions`, `eventSourceInit`, elicitation actions, `roots`, `sampling`, `logging/setLevel`, `sendLoggingMessage`, `resources/subscribe`/`unsubscribe` requests, dynamic client registration.

See `mastra-mcp` for v2 usage.

## Mastra Cloud to Mastra Platform

| Area | Mastra Cloud | Mastra Platform |
|---|---|---|
| Products | One project | Observability, Studio, Server on one project |
| Deploys | Auto-deploy on push | `mastra deploy` or the GitHub integration |
| Storage | Cloud Store (managed LibSQL) | Your database, or a platform hosted database |
| Observability | Logger-based | `Observability` with `MastraPlatformExporter` |
| Tokens | Cloud tokens | New tokens: `mastra auth tokens create` |

Steps:

1. `npm install -g mastra@latest`, then the user runs `mastra auth login`. Check `mastra build` passes.
2. Cloud Store users: export the database from the dashboard (**Runtime, Settings, Storage, Export Database**) and load it with `sqlite3 mydb.db < ~/Downloads/mastra-cloud-dump.sql`, or dump with the Turso CLI using `MASTRA_STORAGE_URL` and `MASTRA_STORAGE_AUTH_TOKEN`. Load into a new libSQL database and point `LibSQLStore` at it through env vars.
3. Replace logger-only tracing with `observability: new Observability({...})` and `MastraStorageExporter`, `MastraPlatformExporter`, `SensitiveDataFilter`.
4. Deploy with `mastra deploy` (the guide still shows the deprecated `mastra studio deploy` and `mastra server deploy`; use `mastra deploy`).
5. Set up CI, then decommission the old Cloud project.

The Cloud guide says the platform does not host a database for you; current platform docs offer hosted Turso, Neon, and Postgres (`mastra env db create`). See `mastra-platform`.
