# Agent API reference

Distilled from `https://mastra.ai/reference/agents/agent.md` and `https://mastra.ai/reference/agents/generate.md`. Verify against the installed version before relying on an option.

## Contents

- Constructor options
- generate() and stream() options
- Result fields
- Instance methods
- Mastra instance accessors

---

## Constructor options: `new Agent({...})`

Import: `import { Agent } from '@mastra/core/agent'`

Most fields accept a static value or a function `({ requestContext }) => value | Promise<value>`.

| Option | Type (simplified) | Notes |
|---|---|---|
| `id` | `string` | Required. Unique. Used by `mastra.getAgentById()`. |
| `name` | `string` | Required. Display name. |
| `instructions` | `string \| string[] \| SystemMessage \| SystemMessage[] \| fn` | Required. System prompt. Message objects accept `providerOptions` (for example Anthropic `cacheControl`). |
| `model` | `'provider/model' \| config \| fallback array \| fn` | Required. Router string, provider instance, or `[{ model, maxRetries }]` fallback list. |
| `description` | `string` | Shown to supervisors when this agent is a subagent. |
| `tools` | `Record<string, Tool> \| fn({ requestContext, mastra })` | The object key becomes `toolName` in streams. |
| `agents` | `Record<string, Agent> \| fn` | Subagents. Exposed as `agent-<key>` tools. |
| `workflows` | `Record<string, Workflow> \| fn` | Exposed as `workflow-<key>` tools. |
| `memory` | `Memory \| fn` | From `@mastra/memory`. |
| `defaultOptions` | `AgentExecutionOptions \| fn` | Defaults merged into every `generate()`/`stream()` call. |
| `inputProcessors` / `outputProcessors` | `(Processor \| ProcessorWorkflow)[] \| fn` | See `mastra-processors-guardrails`. |
| `maxProcessorRetries` | `number` | How often a processor may request an LLM step retry. |
| `scorers` | `MastraScorers \| fn` | Live evaluation. See `mastra-evals`. |
| `hooks` | `{ beforeToolCall?, afterToolCall? }` | Runs around every tool call. `beforeToolCall` may return `{ proceed: false, output }`. |
| `transform` | `ToolPayloadTransformPolicy` | Shared redaction policy for display and transcript targets. |
| `voice` | `IMastraVoice \| fn` | See `mastra-voice`. |
| `requestContextSchema` | Standard JSON Schema (zod etc.) | Validates `requestContext` at call start. Throws `MastraError` before any LLM call. |
| `scopes` | `string[] \| fn` | `<type>:<value>` scopes the run acts as. |
| `metadata` | `Record<string, unknown> \| fn` | Classification for clients. |
| `notifications` | `object` | Durable notification signal delivery. See `mastra-signals`. |
| `editor` | `false \| { instructions?, tools?, model? }` | Which fields Studio Editor may override. See `mastra-studio-editor`. |

---

## Execution options: `agent.generate(messages, options)` and `agent.stream(messages, options)`

`messages`: `string | string[] | CoreMessage[] | UIMessage[]`.

| Option | Notes |
|---|---|
| `maxSteps` | Max loop iterations (model call + tool calls). |
| `stopWhen` | Stop condition predicate(s). If it throws, `fullStream` rejects. |
| `onIterationComplete(ctx)` | Return `{ continue: false }` to stop, or `{ feedback }` to steer the next iteration. `ctx` has `iteration`, `text`, `toolCalls`, `finishReason`, `isFinal`. |
| `isTaskComplete` | `{ scorers, strategy: 'all' \| 'any', onComplete, parallel, timeout }` completion check. |
| `memory` | `{ resource, thread, options? }`. `thread` may be a string or `{ id, title, metadata }`. |
| `requestContext` | `RequestContext` instance with per-request values. |
| `instructions` / `system` | Override or supplement the agent instructions for this call. |
| `context` | Extra `ModelMessage[]` to include. |
| `structuredOutput` | `{ schema, model?, errorStrategy?, fallbackValue?, jsonPromptInjection? }`. See `mastra-structured-output`. |
| `toolChoice` | `'auto' \| 'none' \| 'required' \| { type: 'tool', toolName }` |
| `activeTools` | Tool names allowed this call. |
| `toolsets` / `clientTools` | Extra tools for this call. Client tools have no `execute`. |
| `toolCallConcurrency` | Default 1 when approval may be required, else 10. |
| `requireToolApproval` | Suspend every tool call for approval. See `mastra-agent-approval-hitl`. |
| `autoResumeSuspendedTools` | Resume a suspended tool from the next user message. Needs memory. |
| `hooks` | Per-call tool hooks. Merged per key with agent hooks. |
| `prepareStep` | Callback before each step (swap model, tools, messages). |
| `delegation` | `{ onDelegationStart, onDelegationComplete, messageFilter }` for subagents. |
| `modelSettings` | `temperature`, `maxOutputTokens`, `topP`, `topK`, `presencePenalty`, `frequencyPenalty`, `stopSequences`, `maxRetries`, `timeout: { totalMs, stepMs, firstChunkMs }`. |
| `providerOptions` | `{ openai: { reasoningEffort } }`, `{ anthropic: {...} }`, etc. |
| `inputProcessors` / `outputProcessors` | Override the agent's processors for this call. |
| `scorers`, `returnScorerData` | Per-call scoring with optional sampling `{ type: 'ratio', rate }`. |
| `tracingOptions` | `{ rootSpanName, metadata, tags, requestContextKeys, traceId, parentSpanId }`. |
| `abortSignal` | Cancels the run, including in-flight subagent runs. |
| `onChunk`, `onStepFinish`, `onFinish`, `onError`, `onAbort` | Lifecycle callbacks. |
| `runId` | Set your own run id. |
| `savePerStep` | Persist messages after each step. Disabled with observational memory. |

---

## Result fields

`generate()` resolves to:

| Field | Notes |
|---|---|
| `text` | Final text. |
| `object` | Parsed structured output when `structuredOutput` is set. |
| `usedFallbackValue` | True when `errorStrategy: 'fallback'` substituted `fallbackValue`. |
| `toolCalls` | Chunk format: `{ type: 'tool-call', runId, from, payload: { toolCallId, toolName, args } }`. |
| `toolResults` | Chunk format: `payload: { toolCallId, toolName, result, isError }`. |
| `steps` | Per-step `text`, `toolCalls`, `toolResults`, `finishReason`, `usage`. |
| `usage` | Token usage totals. |
| `finishReason` | For example `stop`, `tool-calls`, `suspended`. |

`stream()` resolves to a `MastraModelOutput` with `textStream`, `fullStream`, `objectStream`, `runId`, and promises (`text`, `toolCalls`, `toolResults`, `steps`, `usage`, `object`). See `mastra-streaming`.

---

## Instance methods (selection)

| Method | Purpose |
|---|---|
| `getInstructions({ requestContext })` | Resolve instructions. |
| `getModel({ requestContext })` | Resolve the model. |
| `listTools()`, `listWorkflows()`, `listAgents()`, `listScorers()` | Inspect capabilities. |
| `getMemory()` | Memory instance. |
| `network(messages, options)` | Routing-agent network execution. See `mastra-multi-agent`. |
| `resumeStream(resumeData, { runId })` | Resume a suspended tool call. |
| `approveToolCallGenerate()` / `declineToolCallGenerate()` | Approval flow. See `mastra-agent-approval-hitl`. |
| `listSuspendedRuns()` | Find runs waiting on approval or input. |
| `sendSignal()`, `subscribeToThread()` | Thread signals. See `mastra-signals`. |

## Mastra instance accessors

| Method | Purpose |
|---|---|
| `mastra.getAgentById(id)` | Preferred lookup by `id`. |
| `mastra.getAgent(key)` | Lookup by registration key. |
| `mastra.listAgents()` | All registered agents. |
