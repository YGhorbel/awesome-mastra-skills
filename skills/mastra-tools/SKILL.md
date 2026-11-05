---
name: mastra-tools
description: "Define, attach, and control Mastra tools: createTool with inputSchema, outputSchema, and execute(inputData, context), schemas in Zod, Valibot, or ArkType, output validation, toModelOutput, transform redaction, client tools, tool hooks, lifecycle hooks, toolChoice and activeTools, built-in tools, code mode, and dynamic tool search. Use this skill whenever the user wants an agent to call an API, query a database, run a function, fetch a web page, search the web, ask the user a question, track tasks, or run many tools in one sandboxed call. Triggers on createTool, @mastra/core/tools, tool schema, beforeToolCall, afterToolCall, onInputAvailable, onOutput, toModelOutput, renderOnly, clientTools, toolChoice, activeTools, webSearchTool, webFetchTool, askUserTool, submitPlanTool, task tools, createCodeMode, QuickJsCodeModeTransport, IsolatedVmCodeModeTransport, ToolSearchProcessor. Also triggers when an agent ignores its tools, retries a tool forever, or has too many tools."
license: Apache-2.0
metadata:
  category: agents
  catalog_summary: "createTool, schemas, execute context, hooks, client tools, built-in tools, code mode, and dynamic tool search"
  display_order: 2
  docs: https://mastra.ai/docs/agents/tools
---

# Mastra Tools

Define tools with `createTool()`, attach them to agents, and control how the model sees, calls, and receives them.

---

## When to use

- Writing a new tool or fixing a `createTool({...})` definition
- Choosing a schema library (Zod, Valibot, ArkType) for tool input and output
- Shaping what the model receives (`toModelOutput`) versus what the UI or transcript receives (`transform`)
- Tools the browser runs (client tools, `renderOnly`)
- Logging, auditing, or blocking tool calls with agent `hooks` or tool lifecycle hooks
- Forcing or limiting tools per call with `toolChoice` and `activeTools`
- Adding built-in tools: web search, web fetch, ask user, submit plan, task tracking
- Running multi-tool computations in one call with code mode
- Agents with large tool libraries that need on-demand tool loading

## When NOT to use

- Agent definition, instructions, and `generate()`/`stream()` basics (use `mastra-agents`)
- Approval gates and `suspend()`/resume flows in depth (use `mastra-agent-approval-hitl`)
- Typed final answers from the agent (use `mastra-structured-output`)
- Tools from MCP servers, or exposing your tools over MCP (use `mastra-mcp`)
- Ready-made third-party tools and Mastra Connect (use `mastra-tool-integrations`)
- Subagents exposed as tools and delegation (use `mastra-multi-agent`)
- Retrieval tools such as vector query (use `mastra-rag`)
- Sandboxes and workspace tools (use `mastra-workspace-sandbox`)
- Tools inside workflow steps (use `mastra-workflows`)

---

## Required inputs

- What the tool does, in one sentence the model can act on
- Input fields and their types, and which are optional
- Output fields the app needs, and what the model actually needs to see
- Side effects (writes, payments, emails) and whether a retry is safe
- Secrets or per-user values the tool needs (pass them through `requestContext`, not input)
- Where it runs: server (`execute`), client (no `execute`), or display only (`renderOnly`)

---

## The framework: define, attach, control

### 1. Define

```typescript
// src/mastra/tools/weather-tool.ts
import { createTool } from '@mastra/core/tools'
import { z } from 'zod'

export const weatherTool = createTool({
  id: 'weather-tool',
  description: 'Fetches weather for a location',
  inputSchema: z.object({
    location: z.string(),
  }),
  outputSchema: z.object({
    location: z.string(),
    temperatureCelsius: z.number(),
    conditions: z.string(),
  }),
  execute: async ({ location }, { abortSignal }) => {
    const response = await fetch(`https://wttr.in/${location}?format=j1`, {
      signal: abortSignal,
    })
    const data = await response.json()
    return {
      location,
      temperatureCelsius: Number(data.current_condition[0].temp_C),
      conditions: data.current_condition[0].weatherDesc[0].value,
    }
  },
})
```

`execute` has exactly one signature: `execute(inputData, context)`. The first argument is validated against `inputSchema`. The second carries `requestContext`, `abortSignal`, `tracingContext`, `agent`, `workflow`, `mcp`, and `observe`. Omit it when unused. Other shapes are outdated.

### 2. Attach

```typescript
import { Agent } from '@mastra/core/agent'
import { weatherTool } from '../tools/weather-tool'

export const weatherAgent = new Agent({
  id: 'weather-agent',
  name: 'Weather Agent',
  instructions: `
    You are a helpful weather assistant.
    Use the weatherTool to fetch current weather data.`,
  model: 'openai/gpt-6.1-sol',
  tools: { weatherTool },
})
```

The object key is the `toolName` in streams and traces, not the tool `id`. `tools: { weatherTool }` yields `weatherTool`. `tools: { [weatherTool.id]: weatherTool }` yields `weather-tool`. Subagents become `agent-<key>`, workflows become `workflow-<key>`.

### 3. Control per call

```typescript
await agent.generate('Check the forecast', {
  toolChoice: 'required',          // 'auto' | 'none' | 'required' | { type: 'tool', toolName }
  activeTools: ['weatherTool'],     // keys, not ids
})
```

### The tool surface at a glance

| Need | Use |
|---|---|
| Model sees a smaller or multimodal result | `toModelOutput` |
| UI stream or transcript hides secrets | `transform.display` / `transform.transcript` |
| Side effect already happened, schema mismatch | `outputValidation: 'warn'` |
| Exact schema-matching arguments | `strict: true` |
| Browser runs the tool | omit `execute`, or pass via `clientTools` |
| Browser only renders a card | `renderOnly: true` |
| Log, audit, or block every call | agent `hooks.beforeToolCall` / `afterToolCall` |
| React to streaming input or output of one tool | `onInputStart`, `onInputDelta`, `onInputAvailable`, `onOutput` |
| Human approval | `requireApproval: true` (see `mastra-agent-approval-hitl`) |
| Many tools, one sandboxed call | `createCodeMode()` |
| Hundreds of tools | `ToolSearchProcessor` |

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/` and the installed `createTool` types. Otherwise fetch `https://mastra.ai/docs/agents/tools.md` and `https://mastra.ai/reference/tools/create-tool.md`. Trust these over memory.
2. **Write the description.** One short sentence on what the tool does and its main use case. The model picks tools from descriptions and schema field names.
3. **Write the schemas.** Use any Standard JSON Schema library. Add `.describe()` on non-obvious fields. Make optional fields explicit.
4. **Implement `execute(inputData, context)`.** Destructure input fields. Pass `context.abortSignal` to `fetch`. Read secrets and tenant ids from `context.requestContext`. Return only what `outputSchema` declares.
5. **Decide what the model sees.** Add `toModelOutput` when the raw result is large. Add `transform` when the UI or transcript must not see raw values.
6. **Mark side effects.** Use `outputValidation: 'warn'` for non-idempotent tools. Gate destructive tools with `requireApproval: true`.
7. **Attach to the agent** with a deliberate key, and name each tool in the instructions with the condition for calling it.
8. **Add guards.** Agent `hooks` for audit and policy. `toolChoice`/`activeTools` per call when the route already knows what is allowed.
9. **Scale.** Over roughly a dozen related tools: code mode for multi-tool computations, or `ToolSearchProcessor` for large catalogs (see `references/built-in-and-advanced.md`).
10. **Test the tool alone** with `npx mastra api tool execute weather-tool '{"location":"San Francisco"}'` against `npx mastra dev`. Run `npx mastra api tool execute --schema` before building other inputs. Then test through the agent in Studio.

---

## Deep dive: client tools and hooks

A tool without `execute` is a client tool. The run stops with `finishReason: 'tool-calls'` until the client sends the result on a new request. Pick the pattern by what the model needs back:

- The model needs the client's result: omit `execute`. The client runs it and sends a follow-up request.
- The client only renders the call: set `renderOnly: true`. Mastra returns `{ acknowledged: true }` and the agent continues. Do not add an incompatible `outputSchema`.
- The tool needs a structured answer from the user: call `suspend()` in `execute` (see `mastra-agent-approval-hitl`).

Subagents cannot run client tools. Give client tools to the supervisor.

Agent-level hooks apply to every tool source (assigned, memory, toolsets, client, agent and workflow tools, workspace tools):

```typescript
export const guardedAgent = new Agent({
  id: 'guarded-agent',
  name: 'guarded-agent',
  instructions: 'Run shell commands for the user.',
  model: 'openai/gpt-6.1-sol',
  hooks: {
    beforeToolCall: ({ toolName, input }) => {
      const command = (input as { command?: string }).command ?? ''
      if (toolName === 'execute_command' && command.includes('rm -rf')) {
        return { proceed: false, output: 'Command blocked by policy.' }
      }
    },
    afterToolCall: ({ toolName, output, error }) => {
      console.log(`Finished ${toolName}`, { output, error })
    },
  },
})
```

Per-call `hooks` on `generate()`/`stream()` merge per key with agent hooks. Tool lifecycle hook errors are logged and never fail the call.

---

## Failure patterns

- **Old `execute` shapes** such as `execute: async ({ context }) => ...`. Use `execute: async (inputData, context) => ...`.
- **`activeTools` or `toolChoice.toolName` uses the tool `id`.** They use the object key from `tools: {...}`. Use matching keys.
- **The model never calls the tool.** The instructions do not mention it, or the description is vague. Name the tool and when to call it.
- **The model retries a payment or order.** The result failed `outputSchema` and became a validation error. Set `outputValidation: 'warn'` or fix the schema.
- **Huge tool results bloat context.** Return the full object to the app and use `toModelOutput` to send a short summary.
- **Secrets leak into the UI stream.** `toModelOutput` does not affect display. Add `transform.display` and `transform.transcript`.
- **Client tool inside a subagent.** The subagent stops and returns `subAgentPendingToolCalls`. Move the tool to the supervisor.
- **Trusting `onOutput` for client results.** The server does not validate client output against `outputSchema`. Treat it as untrusted and keep the hook idempotent.
- **`webSearchTool` on an unsupported provider.** The run fails with `MastraError`. Use OpenAI, Anthropic, Google Gemini, or xAI models.
- **Code mode without a boundary.** `createCodeMode()` needs a `sandbox`, a workspace sandbox, or an isolating transport. `LocalSandbox` runs model code on the host.
- **Task tools without memory.** They return an error. Add `memory` to the agent.
- **Too many tools on one agent.** Selection degrades. Use `ToolSearchProcessor`, code mode, or split into subagents.

---

## Output format

A finished tool delivery contains:

- `src/mastra/tools/<tool-id>.ts` exporting the tool, with `id`, `description`, `inputSchema`, `outputSchema`, `execute`
- The tool attached to an agent under a deliberate key, and named in the agent instructions
- Any secrets read from `requestContext` or env vars, listed in `.env.example`
- Side-effect handling: `outputValidation`, approval, or idempotency noted
- Evidence it works: a `npx mastra api tool execute` call, then an agent run in Studio

---

## Reference files

- [`references/api.md`](references/api.md) - `createTool()` options, execution context, lifecycle hooks, agent hooks, and per-call tool options.
- [`references/built-in-and-advanced.md`](references/built-in-and-advanced.md) - Built-in tools, code mode and transports, `ToolSearchProcessor`.
- [`references/examples.md`](references/examples.md) - Complete tools: API tool, redacting tool, client and render-only tools, code mode agent, tool search agent.
- [`references/checklist.md`](references/checklist.md) - Pre-production checklist for tools.

**Live docs**

- https://mastra.ai/docs/agents/tools
- https://mastra.ai/reference/tools/create-tool
- https://mastra.ai/docs/agents/code-mode
- https://mastra.ai/reference/tools/create-code-mode
- https://mastra.ai/reference/tools/ask-user-tool
- https://mastra.ai/reference/tools/submit-plan-tool
- https://mastra.ai/reference/tools/task-tools
- https://mastra.ai/reference/processors/tool-search-processor
