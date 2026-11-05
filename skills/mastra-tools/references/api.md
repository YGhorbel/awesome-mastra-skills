# Tools API reference

Distilled from `https://mastra.ai/reference/tools/create-tool.md`, `https://mastra.ai/docs/agents/tools.md`, and `https://mastra.ai/reference/agents/generate.md`. Verify against the installed version before relying on an option.

## Contents

- createTool() options
- Execution context
- toModelOutput return shapes
- transform phases
- Tool lifecycle hooks
- Agent-level hooks
- Per-call tool options
- toolName keys
- MCP annotations

---

## `createTool({...})` options

Import: `import { createTool } from '@mastra/core/tools'`. Returns a `Tool` object.

| Option | Type | Notes |
|---|---|---|
| `id` | `string` | Unique identifier. |
| `title` | `string` | Display name for UIs. Not sent to the model. Travels on `tool-call` chunks and stored tool parts. MCP clients see it as the tool title. |
| `description` | `string` | What the tool does. The model uses it to decide when to call. |
| `inputSchema` | `StandardJSONSchemaV1` | Zod, Valibot (via `toStandardJsonSchema`), ArkType, or any Standard JSON Schema library. |
| `outputSchema` | `StandardJSONSchemaV1` | Expected `execute` return shape. |
| `execute` | `(inputData, context) => Promise<output>` | Tool logic. Omit for client tools. |
| `renderOnly` | `boolean` | Stream a display-only call and return `{ acknowledged: true }`. Cannot be used with `execute`. |
| `strict` | `boolean` | Ask supporting model adapters for strict schema-matching arguments. Ignored elsewhere. |
| `outputValidation` | `'strict' \| 'warn'` | Default `'strict'`: a failed result becomes a validation error object. `'warn'`: log and return the real result. Both log a warning. |
| `toModelOutput` | `(output) => unknown` | Transform the result before the model sees it. App code still gets the raw result. |
| `transform` | `ToolPayloadTransform` | Per-target (`display`, `transcript`) transforms for UI streams and user-visible transcripts. |
| `suspendSchema` | `StandardJSONSchemaV1` | Shape of the payload passed to `suspend()`. |
| `resumeSchema` | `StandardJSONSchemaV1` | Shape of `resumeData`. Used by `autoResumeSuspendedTools`. |
| `requireApproval` | `boolean` | Pause for approval. Input is validated first; invalid input goes back to the model without approval. |
| `beforeApproval` | `(input, context) => void \| { proceed: false, output }` | Runs before the approval gate. Return `{ proceed: false, output }` to reject without pausing. If it throws, the call proceeds to the gate. |
| `mcp` | `{ annotations?, _meta? }` | MCP behavior hints and metadata. |
| `requestContextSchema` | `StandardJSONSchemaV1` | Validates request context before `execute` runs. Failure returns an error object. |
| `providerOptions` | `Record<string, Record<string, unknown>>` | Provider-specific options sent when this tool is used. |
| `inputExamples` | `Array<{ input: Record<string, unknown> }>` | Example inputs for providers that support them. |
| `background` | `ToolBackgroundConfig` | Run in the background while the conversation continues. See `mastra-harness`. |
| `onInputStart`, `onInputDelta`, `onInputAvailable`, `onOutput` | functions | Lifecycle hooks. See below. |

Runtime-populated fields such as `mastra` and `mcpMetadata` are set by Mastra. Do not configure them.

---

## Execution context (second `execute` argument)

| Field | Notes |
|---|---|
| `requestContext` | `RequestContext` with per-request values (user id, tenant, tokens). |
| `abortSignal` | Pass to `fetch` and long operations. |
| `agent` | Agent-specific context when an agent runs the tool. |
| `workflow` | Workflow context (`state`, `setState`, `suspend`, and so on). |
| `mcp` | MCP context, for example elicitation. |
| `observe` | Helpers for child spans and structured logs. Always provided; no-op without tracing. |

`tracingContext` is also supplied by the runtime.

---

## `toModelOutput` return shapes

- `{ type: 'text', value }`
- `{ type: 'json', value }`
- `{ type: 'content', value: [...] }` with parts `text`, `image-url`, `image-data`, `file-url`, `file-data`, `file-id`, `image-file-id`, or `custom`

It also applies to client tools. For `clientTools`, the mapping runs on the client and is sent back with the raw result. For server-defined tools without `execute`, the server applies it to the incoming result.

---

## `transform` phases

Targets: `display` (browser-facing streams) and `transcript` (user-visible transcript messages).

Phases: `input`, `inputDelta`, `output`, `error`, `approval`, `suspend`, `resume`.

- Only the phases you define change.
- If a configured transform fails, Mastra does not fall back to the raw payload.
- Input deltas are suppressed when no safe `inputDelta` transform exists.
- For a DurableAgent that can finish after a restart, declare transcript redaction on the tool, not per invocation.
- The agent constructor accepts a shared `transform` policy for many tools.

---

## Tool lifecycle hooks

| Hook | Receives | When |
|---|---|---|
| `onInputStart` | `ToolCallOptions` (`toolCallId`, `messages`, `abortSignal`) | Input streaming begins |
| `onInputDelta` | `{ inputTextDelta } & ToolCallOptions` | Each input chunk |
| `onInputAvailable` | `{ input } & ToolCallOptions` | Input parsed and validated |
| `onOutput` | `{ output, toolName } & Omit<ToolCallOptions, 'messages'>` | After successful server execution, or a successful client result on the follow-up request |

Order for a server tool: `onInputStart`, `onInputDelta` (repeated), `onInputAvailable`, `execute`, `onOutput`.

Rules:

- Hook errors are caught and logged. They never fail the call.
- `onOutput` does not run on error results.
- Client results are not validated against `outputSchema`. Treat `output` as untrusted.
- Retried requests run `onOutput` again. Keep it idempotent.
- A follow-up request with only the tool result (no assistant tool call) does not fire `onOutput`. `@mastra/client-js` sends both.

---

## Agent-level hooks

Set on `new Agent({ hooks })` or per call in `generate()`/`stream()` options.

| Hook | Receives | Return |
|---|---|---|
| `beforeToolCall` | `{ toolName, input, ... }` plus execution context | `{ proceed: false, output }` skips the tool; `output` becomes the result |
| `afterToolCall` | `{ toolName, output, error }` | Runs on success and failure. Errors are re-thrown after the hook. |

Per-call hooks override matching agent hooks per key. Passing only `beforeToolCall` per call keeps the agent's `afterToolCall`.

---

## Per-call tool options (`generate()` / `stream()`)

| Option | Notes |
|---|---|
| `toolChoice` | `'auto'` (default), `'none'`, `'required'`, or `{ type: 'tool', toolName }` |
| `activeTools` | Array of tool keys active this call. Undefined means all. |
| `toolsets` | Extra tool sets for this call. |
| `clientTools` | Client-side tools for this call. |
| `toolCallConcurrency` | Default 1 when approval may be required, otherwise 10. |
| `prepareStep` | Callback before each step. |
| `hooks` | Per-call `beforeToolCall` / `afterToolCall`. |
| `requireToolApproval` | Gate every tool call. See `mastra-agent-approval-hitl`. |
| `autoResumeSuspendedTools` | Resume suspended tools from the next user message. Needs memory. |

---

## `toolName` keys

| Source | `toolName` |
|---|---|
| `tools: { weatherTool }` | `weatherTool` |
| `tools: { [weatherTool.id]: weatherTool }` | `weather-tool` |
| `tools: { 'my-custom-name': weatherTool }` | `my-custom-name` |
| `agents: { weather }` | `agent-weather` |
| `workflows: { research }` | `workflow-research` |

Subagent chunks also carry the subagent's real `id` in `data-tool-agent` chunks.

Mastra instance accessors: `mastra.getTool()`, `mastra.getToolById()`, `mastra.listTools()`.

---

## MCP annotations

```typescript
mcp: {
  annotations: {
    title: 'Weather Lookup',
    readOnlyHint: true,
    destructiveHint: false,
    idempotentHint: true,
    openWorldHint: true,
  },
  _meta: { version: '1.0.0', category: 'weather' },
}
```

Defaults: `readOnlyHint` false, `destructiveHint` true, `idempotentHint` false, `openWorldHint` true. See `mastra-mcp` for serving tools over MCP.
