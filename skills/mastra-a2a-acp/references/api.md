# A2A, ACP, and SDK agents API reference

Distilled from `https://mastra.ai/docs/connections/a2a.md`, `https://mastra.ai/docs/connections/acp.md`, `https://mastra.ai/docs/connections/sdk-agents.md`, `https://mastra.ai/reference/acp/acp-agent.md`, and `https://mastra.ai/reference/acp/create-acp-tool.md`. There is no dedicated A2A reference page; options below come from the A2A docs page. Verify against installed types.

## Contents

- A2AAgent
- A2A client (`MastraClient`)
- A2A server configuration
- AcpAgent
- createACPTool()
- SDK agents

---

## A2AAgent

`import { A2AAgent } from '@mastra/core/a2a'`. Mastra supports A2A v0.3.0 and v1.0.

| Option | Notes |
|---|---|
| `url` | Full agent card URL, or a domain (reads `/.well-known/agent-card.json`). |
| `protocolVersion` | Omit for v0.3. `'1.0'` sends `A2A-Version: 1.0`. |
| `headers` | For example `Authorization`. |
| `retries`, `backoffMs`, `maxBackoffMs`, `timeoutMs` | Request resilience. |
| `credentials`, `fetch`, `abortSignal` | Custom fetch behavior and cancellation. |
| `verifyAgentCard` | `{ verify: async (card, context) => void }`. Throw to refuse. `context.cardUrl` available. |

Behavior: fetches and caches the card, reads execution URL and capabilities, calls `message/send` / `message/stream` (v0.3) or `SendMessage` / `SendStreamingMessage` (v1.0), converts tasks, artifacts, and status updates into subagent results.

Methods: `generate(message, { runId })`, `stream(...)` (buffered fallback without streaming capability), `resumeGenerate(data, { runId })`, `resumeStream(...)`.

Suspension: remote `input-required` or `auth-required` returns `finishReason: 'suspended'` with `suspendPayload`.

Protocol types: v1.0 types and codecs from `@mastra/core/a2a/v1`; `@mastra/core/a2a/client` stays on v0.3.

---

## A2A client (`MastraClient`)

`import { MastraClient } from '@mastra/client-js'`. `new MastraClient({ baseUrl, headers, apiPrefix? })`.

`client.getA2A(agentId)` (v0.3):

| Method | Notes |
|---|---|
| `getAgentCard({ verifySignature? })` | `verifySignature: { algorithms: ['ES256'], keyProvider: async ({ kid, jku }) => jwk }` |
| `sendMessageStream({ message })` | SSE events: task status and `artifact-update`. |
| `resubscribeTask({ id })` | Live updates for an in-progress task after a disconnect. |
| `setTaskPushNotificationConfig({ taskId, pushNotificationConfig: { url, token } })` | Needs `capabilities.pushNotifications`. |

Message shape: `{ kind: 'message', role: 'user', messageId, parts: [{ kind: 'text', text }] }`.

`client.getA2AV1(agentId)` (v1.0): `getAgentCard()`, `sendMessage()`, `sendMessageStream()`, `getTask()`, `listTasks(ListTasksRequest.fromJSON({ contextId, pageSize }))`, `cancelTask()`, `resubscribeTask()`.

---

## A2A server configuration

Any agent registered on `Mastra` gets an agent card and execution endpoint (`/api/.well-known/<id>/agent-card.json`, `/api/a2a/<id>`). Card fields include `protocolVersion`, `name`, `description`, `url`, `version`, `provider`, `capabilities` (`streaming`, `pushNotifications`, `stateTransitionHistory`), `defaultInputModes`, `defaultOutputModes`, `skills`.

Card signing:

```typescript
new Mastra({
  server: {
    a2a: {
      agentCardSigning: {
        privateKey: process.env.A2A_AGENT_CARD_PRIVATE_KEY!,
        protectedHeader: { alg: 'ES256', kid: 'agent-card-key' },
      },
    },
  },
})
```

HITL as a server: an agent suspension (tool approval or `suspend()`) maps to task state `input-required`, with a data part carrying `suspendPayload` and `resumeSchema`. A follow-up message with the same `taskId` resumes it (data part, JSON text, or plain text). Requires server storage.

Push notifications fire on `completed`, `failed`, `canceled`, `rejected`, `input-required`, `auth-required`. Best effort. In memory.

---

## AcpAgent

`import { AcpAgent } from '@mastra/acp'`. Requires `@mastra/core` 1.34.0+.

| Option | Default | Notes |
|---|---|---|
| `id` | | Subagent id. |
| `name` | `id` | |
| `description` | | Shown to the parent model. |
| `command` | | Executable to spawn. |
| `args` | `[]` | |
| `env` | | Merged with the current process env. |
| `cwd` | `process.cwd()` | Process and session cwd; default filesystem base path. |
| `session` | cwd, no MCP servers | `Partial<NewSessionRequest>` |
| `initialize` | Mastra client info, read/write fs capabilities | `Partial<InitializeRequest>` |
| `authMethodId` | | ACP auth method run before session creation. |
| `persistSession` | `true` | `false` stops the process after each prompt. |
| `onPermissionRequest` | first option, or cancel | `(request) => Promise<RequestPermissionResponse>` |
| `createClient` | | `(defaultClient) => Client` to add `extMethod`/`extNotification`. |
| `workspace` | `LocalFilesystem` at `cwd` | Used for ACP file read/write requests only. |
| `model` | | Selected after session creation (`session/set_model`). |

Properties: `id`, `name`, `description`, `connection`. Methods: `generate()`, `stream()` (ACP `agent_message_chunk` becomes `text-delta`), `getAvailableModels()`, `setModel(modelId)`. `resumeGenerate()` and `resumeStream()` throw.

Permission response shapes: `{ outcome: { outcome: 'selected', optionId } }` or `{ outcome: { outcome: 'cancelled' } }`.

Compatible agents from the docs:

| Agent | `command` | `args` |
|---|---|---|
| Claude Code (bridge) | `npx` | `['@agentclientprotocol/claude-agent-acp']` |
| Cline | `cline` | `['--acp']` |
| OpenCode | `opencode` | `['acp']` |
| Gemini CLI | `gemini` | `['--acp']` |

---

## createACPTool()

`import { createACPTool } from '@mastra/acp'`. Same options as `AcpAgent` (`id`, `description`, `command`, `args`, `env`, `cwd`, `session`, `initialize`, `authMethodId`, `persistSession`, `onPermissionRequest`, `createClient`, `workspace`, `model`).

- Input: `{ task: string }`. Output: `{ output: string }`.
- Suspend payload: `{ permissionRequest: { title, options: { optionId, name }[] } }`. Resume payload: `{ optionId, outcome: 'selected' | 'cancelled' }`.
- Each execution creates a connection and starts the command.
- Uses the current Mastra workspace from the execution context when available.

---

## SDK agents

| Class | Package | Peer deps | Credential | Configure |
|---|---|---|---|---|
| `ClaudeSDKAgent` | `@mastra/claude` | `@anthropic-ai/claude-agent-sdk`, `zod` | `ANTHROPIC_API_KEY` | `sdkOptions: { model, cwd, mcpServers, allowedTools }` |
| `CursorSDKAgent` | `@mastra/cursor` | `@cursor/sdk` | `CURSOR_API_KEY` | `sdkOptions: { apiKey, model: { id }, local: { cwd }, mcpServers }`, or `agent` |
| `OpenAISDKAgent` | `@mastra/openai` | `@openai/agents`, `zod` | `OPENAI_API_KEY` | `sdkOptions: { name, instructions, model, tools }`, or `agent` |

Common constructor fields: `id`, `name`, `description`. Register on `new Mastra({ agents })` and call with `mastra.getAgentById()`.

Resume with provider-native data: Claude `resumeGenerate({ message, sessionId })`; OpenAI `resumeStream({ message, previousResponseId })` (or conversation/session); Cursor passes `agentId` in resume data.

`structuredOutput`: supported by Claude and OpenAI SDK agents (`result.object`); Cursor throws.

Observability: agent and model spans with SDK-reported usage, tool activity, and (Claude) estimated cost.
