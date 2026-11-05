---
name: mastra-a2a-acp
description: "Connect Mastra to agents that run outside it: consume or expose remote agents over the Agent-to-Agent (A2A) protocol, run ACP coding agents such as Claude Code, Cline, OpenCode, or Gemini CLI as Mastra subagents or tools, and register Claude Agent SDK, Cursor SDK, or OpenAI Agents SDK agents in a Mastra project. Use this skill whenever the user wants a Mastra agent to delegate to a remote agent, call a Mastra agent from another service by agent card, wrap a coding agent CLI as a subagent, or reuse an existing vendor SDK agent with Mastra generate, stream, and observability. Triggers on A2A, agent card, A2AAgent, @mastra/core/a2a, getA2A, getA2AV1, message/send, input-required, push notifications, ACP, Agent Client Protocol, @mastra/acp, AcpAgent, createACPTool, onPermissionRequest, persistSession, SDK agents, ClaudeSDKAgent, @mastra/claude, CursorSDKAgent, @mastra/cursor, OpenAISDKAgent, @mastra/openai. Also triggers when the user asks which connection type to use between MCP, A2A, ACP, and SDK agents."
license: Apache-2.0
metadata:
  category: connections
  catalog_summary: "Choose a connection; A2A remote agents and agent cards; ACP coding agents as subagents or tools; Claude, Cursor, OpenAI SDK agents"
  display_order: 2
  docs: https://mastra.ai/docs/connections/overview
---

# Mastra A2A, ACP, and SDK agents

Pick the right connection type for an agent that lives outside your Mastra code, then wire it as a subagent, tool, or registered agent with correct trust, session, and permission handling.

---

## When to use

- Deciding between MCP, A2A, ACP, and SDK agents
- A Mastra supervisor should delegate to a remote agent owned by another team or vendor (`A2AAgent`)
- Another service should call a Mastra agent through its A2A agent card and endpoint
- Handling A2A long-running tasks: streaming, resubscribe, `input-required`, push notifications
- Signing or verifying A2A agent cards
- Running a coding agent CLI (Claude Code via bridge, Cline, OpenCode, Gemini CLI) as a subagent (`AcpAgent`) or tool (`createACPTool`)
- Controlling ACP permission prompts and file access through a `Workspace`
- Registering a Claude Agent SDK, Cursor SDK, or OpenAI Agents SDK agent in Mastra

## When NOT to use

- Tools and resources from MCP servers, or exposing Mastra over MCP (use `mastra-mcp`)
- Supervisor and subagent patterns among local Mastra agents (use `mastra-multi-agent`)
- Defining a regular Mastra agent (use `mastra-agents`)
- Calling Mastra agents over REST with the client SDK in general (use `mastra-client-sdk`)
- Sandboxed command execution for your own agent (use `mastra-workspace-sandbox`)
- Durable coding-agent runtimes inside Mastra (use `mastra-harness`)

---

## Required inputs

- Who owns the runtime: a remote service (A2A), a local coding-agent process (ACP), or a vendor SDK (SDK agents)
- For A2A: the agent card URL, auth headers, protocol version (`0.3` default, or `1.0`), and trust requirements
- For ACP: the agent's launch command and flags, working directory, permission policy, and session reuse
- For SDK agents: the vendor package, its API key, and model ID in the vendor's format
- Whether the work can pause for human input, and where that input comes from

---

## The framework: choose by who owns the runtime

| Connection | Owner of agent loop | Mastra API | Package |
|---|---|---|---|
| MCP | Mastra (tools come from the server) | `MCPClient`, `MCPServer` | `@mastra/mcp` (see `mastra-mcp`) |
| A2A | Remote service, over HTTP | `A2AAgent`, `MastraClient.getA2A()` | `@mastra/core/a2a`, `@mastra/client-js` |
| ACP | Local coding-agent child process (stdio JSON) | `AcpAgent`, `createACPTool()` | `@mastra/acp` (needs `@mastra/core` 1.34.0+) |
| SDK agents | Vendor SDK in-process | `ClaudeSDKAgent`, `CursorSDKAgent`, `OpenAISDKAgent` | `@mastra/claude`, `@mastra/cursor`, `@mastra/openai` |

All three agent types plug into a parent agent's `agents` map or the `Mastra` registry and return Mastra `generate()`/`stream()` results.

```typescript
import { Agent } from '@mastra/core/agent'
import { A2AAgent } from '@mastra/core/a2a'
import { AcpAgent } from '@mastra/acp'

const remoteWeatherAgent = new A2AAgent({
  url: 'https://weather.example.com/api/.well-known/weather-agent/agent-card.json',
  headers: { Authorization: `Bearer ${process.env.WEATHER_AGENT_TOKEN}` },
})

const codeAgent = new AcpAgent({
  id: 'code-agent',
  name: 'Code Agent',
  description: 'An ACP-compatible coding agent that can inspect and edit files',
  command: 'opencode',
  args: ['acp'],
  cwd: process.cwd(),
})

export const supervisor = new Agent({
  id: 'supervisor',
  name: 'Supervisor',
  instructions: 'Delegate weather questions to the weather agent and code edits to the code agent.',
  model: 'openai/gpt-6.1-sol',
  agents: { remoteWeatherAgent, codeAgent },
})
```

### A2A endpoints Mastra exposes

With the default `apiPrefix` of `/api`, a registered agent `weather-agent` serves:

- Agent card: `/api/.well-known/weather-agent/agent-card.json`
- Execution endpoint: `/api/a2a/weather-agent`

The `A2A-Version` header picks the wire protocol: missing or `0.3` uses v0.3, `1.0` uses v1.0, anything else returns `VersionNotSupported`.

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/` (A2A) and `node_modules/@mastra/acp/dist/docs/` plus installed types. Otherwise fetch `https://mastra.ai/docs/connections/a2a.md`, `https://mastra.ai/docs/connections/acp.md`, `https://mastra.ai/reference/acp/acp-agent.md`, and `https://mastra.ai/docs/connections/sdk-agents.md`. Trust these over memory.
2. **Choose the connection** with the table above. If you only need tools, use MCP instead.
3. **A2A consume:** wrap the card URL in `A2AAgent`. Use the full card URL for multi-agent servers; a bare domain reads `/.well-known/agent-card.json`. Add `headers`, `retries`, `timeoutMs`, and `verifyAgentCard`.
4. **A2A expose:** register the agent on `Mastra` with storage (needed to resume suspended runs). Optionally sign cards with `server.a2a.agentCardSigning`.
5. **ACP:** install the coding agent and confirm its ACP flag in its own docs. Configure `command`, `args`, `cwd`, `persistSession`, and an explicit `onPermissionRequest`.
6. **SDK agents:** install the Mastra package and its peer SDK, set the vendor API key, configure through `sdkOptions` or wrap an existing SDK agent with `agent`.
7. **Attach** as a subagent (`agents: {...}`), a tool (`createACPTool`), or register on `new Mastra({ agents })`.
8. **Handle pauses.** A2A `input-required` returns `finishReason: 'suspended'`; resume with `resumeGenerate()` using the same `runId`. ACP does not support resume.
9. **Test** in Studio and check traces (see `mastra-observability`).

---

## Deep dive: trust and isolation boundaries

- **A2A cards are discovery data from the network.** Use `verifyAgentCard.verify(card, context)` to enforce the expected provider and endpoint, and verify signed cards with `getAgentCard({ verifySignature: { algorithms, keyProvider } })` before delegating.
- **A2A task state is in memory.** A paused task resumes only on the process that suspended it. Without sticky routing, a restart or a second instance fails the follow-up with task-not-found. Push notification configs are also lost on restart.
- **ACP processes are not sandboxed.** File requests made through the protocol go through Mastra's `Workspace`, but the process runs with `cwd` and can reach any file through its own shell. Run it inside a container or remote machine for untrusted tasks.
- **ACP permissions default to allow.** Without `onPermissionRequest`, Mastra selects the first option the agent offers. Supply a handler that picks an explicit option or cancels.
- **SDK agents own their tools.** `ClaudeSDKAgent` ignores Mastra `tools`; add tools through Claude SDK MCP servers (`sdkOptions.mcpServers`, `allowedTools: ['mcp__<server>__<tool>']`). OpenAI SDK tools go in `sdkOptions.tools`. Cursor uses `sdkOptions.mcpServers`.

---

## Failure patterns

- **Bare domain for a multi-agent Mastra server.** `A2AAgent` fetches `/.well-known/agent-card.json` and misses. Pass the full `/api/.well-known/<agent-id>/agent-card.json` URL.
- **Wrong A2A protocol version.** `A2AAgent` and `getA2A()` default to v0.3. Set `protocolVersion: '1.0'` or use `getA2AV1()` when the remote requires v1.0.
- **Resuming an A2A task on another instance.** Task records are in memory. Use sticky routing or a single instance for HITL flows.
- **Expecting `stream()` to stream from a non-streaming card.** It falls back to a buffered result when `capabilities.streaming` is absent.
- **Launching Claude Code as `claude --acp`.** The ACP reference uses the bridge: `command: 'npx', args: ['@agentclientprotocol/claude-agent-acp']`. Check each agent's current ACP flag; they change between releases.
- **Leaving ACP permissions on the default.** The first option is auto-selected. Add `onPermissionRequest`.
- **Calling `resumeGenerate()` on `AcpAgent`.** Not supported; it throws.
- **ACP agent aborting on custom methods.** Unknown extension methods are rejected. Extend the client with `createClient` and `extMethod`/`extNotification`.
- **Passing Mastra tools to `ClaudeSDKAgent`.** Not accepted. Use the Claude SDK `tool()` helper and `createSdkMcpServer()`.
- **`structuredOutput` on `CursorSDKAgent`.** Throws; Cursor's SDK has no schema-constrained output. Claude and OpenAI SDK agents support it.
- **Cursor local agent without a model.** Set `sdkOptions.model`.
- **Unprotected push notification URLs.** Validate the notification `token` and do not point callbacks at internal network targets.

---

## Output format

A finished delivery contains:

- The connection module (for example `src/mastra/agents/remote-weather.ts`, `code-agent.ts`, or `claude-sdk-agent.ts`)
- Wiring into a supervisor's `agents`, a parent's `tools`, or `new Mastra({ agents })`
- Env vars in `.env.example` (remote agent tokens, `A2A_AGENT_CARD_PRIVATE_KEY`, `ANTHROPIC_API_KEY`, `CURSOR_API_KEY`, `OPENAI_API_KEY`)
- Trust controls: card verification, ACP permission handler, workspace or container for ACP
- Evidence: a Studio run of the parent agent delegating successfully, or a client call to the A2A card

---

## Reference files

- [`references/api.md`](references/api.md) - `A2AAgent` options, A2A client methods and server config, `AcpAgent` and `createACPTool()` options, SDK agent constructors.
- [`references/examples.md`](references/examples.md) - Remote A2A subagent with HITL, calling a Mastra A2A endpoint, ACP coding subagent with permission policy, SDK agents with tools.
- [`references/checklist.md`](references/checklist.md) - Pre-production checklist.

**Live docs**

- https://mastra.ai/docs/connections/overview
- https://mastra.ai/docs/connections/a2a
- https://mastra.ai/docs/connections/acp
- https://mastra.ai/docs/connections/sdk-agents
- https://mastra.ai/reference/acp/acp-agent
- https://mastra.ai/reference/acp/create-acp-tool
