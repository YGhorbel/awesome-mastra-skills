# Multi-agent API reference

Distilled from `https://mastra.ai/docs/subagents.md`, `https://mastra.ai/reference/agents/generate.md`, `https://mastra.ai/reference/streaming/agents/stream.md`, `https://mastra.ai/reference/evals/rubric.md`, and `https://mastra.ai/reference/agents/network.md`. Verify against the installed version before relying on an option.

## Contents

- Supervisor configuration
- Delegation config
- onDelegationStart
- onDelegationComplete
- messageFilter
- Result context options
- Iteration and completion options
- createRubricScorer()
- Background subagents and versioning
- agent.network() (deprecated) and migration map

---

## Supervisor configuration

Import: `import { Agent } from '@mastra/core/agent'`. Added in `@mastra/core@1.8.0`.

| Option | Type | Notes |
|---|---|---|
| `agents` | `Record<string, Agent> \| ({ requestContext }) => Record<string, Agent> \| Promise<...>` | Subagents. Each becomes an `agent-<key>` tool. |
| `description` (on each subagent) | `string` | Routing text the supervisor reads. State purpose, return format, and when to use. |
| `defaultOptions.maxSteps` (on each subagent) | `number` | Caps any `maxSteps` the supervisor model passes to a delegation. |
| `defaultOptions.delegation` (on the supervisor) | `DelegationConfig` | Hooks applied to every call. Per-call `delegation` also works. |
| `backgroundTasks.tools.<key>` | `{ enabled, timeoutMs }` | Run that subagent as a background task. Needs the Mastra `backgroundTasks` manager. |
| `memory` | `Memory` | Supervisor memory. Subagent memory is isolated per delegation. |

Subagents also accept `workflows` and `tools` as usual. `workflows` become `workflow-<key>` tools.

---

## Delegation config: `options.delegation`

| Field | Type | Notes |
|---|---|---|
| `onDelegationStart` | `(ctx: DelegationStartContext) => DelegationStartResult \| void \| Promise<...>` | Before each delegation. |
| `onDelegationComplete` | `(ctx: DelegationCompleteContext) => { feedback?, resultText? } \| void \| Promise<...>` | After each delegation. |
| `messageFilter` | `(ctx: MessageFilterContext) => ModelMessage[] \| Promise<ModelMessage[]>` | Filter forwarded messages. |
| `hookErrorStrategy` | `'throw'` | Default behavior continues when a hook throws. `'throw'` fails the delegation instead. |
| `includeSubAgentToolResultsInModelContext` | `boolean` | Include nested tool results and subagent metadata in the supervisor's model context. Default off. |
| `enableResultReferences` | `boolean` | Give each result a reference id (for example `explorer-1`) reusable through the `contextFromRefs` input. |

Hook failures are always recorded on the run's request context at `__mastra_delegationHookErrors` as `{ hook, primitiveId, toolCallId, runId, name, message }[]`.

---

## onDelegationStart

Context:

| Property | Description |
|---|---|
| `primitiveId` | Subagent id being delegated to |
| `prompt` | Prompt the supervisor is sending |
| `iteration` | Current iteration number |
| `requestContext` | Request context the subagent run receives. Shallow copy of the parent's, minus run-scoped identity keys. Set entries here to pass values down. Values must be JSON-serializable for durable agents. |

Return (all optional):

| Field | Effect |
|---|---|
| `proceed: true` | Allow (default) |
| `proceed: false` plus `rejectionReason` | Reject the delegation |
| `modifiedPrompt` | Replace the prompt |
| `modifiedMaxSteps` | Replace the subagent's step budget. Applied after the cap, so it can raise the budget above `defaultOptions.maxSteps`. |
| `threadMetadata` | Metadata on the subagent's thread at creation (filter with `memory.listThreads({ filter: { metadata } })`) |

With `hookErrorStrategy: 'throw'`, a throwing `onDelegationStart` blocks the subagent from running.

---

## onDelegationComplete

Context:

| Property | Description |
|---|---|
| `primitiveId` | Subagent id that ran |
| `result` | `text`, `usage`, `finishReason`, `subAgentToolResults`, `subAgentPendingToolCalls`, `subAgentThreadId`, `subAgentResourceId` when available |
| `success` | Whether the delegation succeeded |
| `error` | Original error on failure |
| `messages` | Collected subagent transcript, including partial messages |
| `bail()` | Stop the supervisor loop immediately |

Return:

| Field | Effect |
|---|---|
| `feedback` | Saved to supervisor memory as an assistant message, available next turn |
| `resultText` | Replaces the tool result text the supervisor sees in this run. On failure it replaces the error text but the result stays failed. Empty string is valid. |

For background-task delegations with retries, this hook can run once per attempt.

---

## messageFilter

Context: `{ messages, primitiveId, prompt }`. Return the filtered `ModelMessage[]`. If it throws, delegation falls back to the unfiltered context (unless `hookErrorStrategy: 'throw'`).

---

## Result context

- By default the supervisor model sees only the subagent's text. Nested tool calls and thread ids stay out of model context but remain in the tool result payload for UIs.
- Subagents cannot run client tools. The run stops with `finishReason: 'tool-calls'` and lists calls in `subAgentPendingToolCalls`.
- Tool approvals and `suspend()` in a subagent surface in the supervisor's stream as `tool-call-approval` or `tool-call-suspended` chunks. The `toolCallId` is the supervisor's delegation call. See `mastra-agent-approval-hitl`.
- `abortSignal` passed to the supervisor is forwarded to subagents.

---

## Iteration and completion options (on `stream()`/`generate()`)

| Option | Notes |
|---|---|
| `maxSteps` | Supervisor iteration limit. |
| `onIterationComplete(ctx)` | `ctx`: `iteration`, `maxIterations`, `text`, `isFinal`, `finishReason`, `toolCalls`, `messages`. Return `{ continue?: boolean, feedback?: string }`. |
| `isTaskComplete.scorers` | `MastraScorer[]`. Each returns 0 or 1. |
| `isTaskComplete.strategy` | `'all' \| 'any'` |
| `isTaskComplete.onComplete` | `(result) => void`. `result.complete` and per-scorer scores. |
| `isTaskComplete.parallel` | Run scorers in parallel. |
| `isTaskComplete.timeout` | Milliseconds to wait for scorers. |
| `isTaskComplete.suppressFeedback` | Mark feedback so consumers can hide it. |

Failed scorer feedback is added to the conversation so the next iteration can fix it.

---

## createRubricScorer()

Import: `import { createRubricScorer } from '@mastra/evals/scorers/prebuilt'`. Added in `@mastra/evals@1.3.0`.

| Parameter | Type | Notes |
|---|---|---|
| `model` | `MastraModelConfig` | Grader model. A smaller model is usually enough. |
| `criteria` | `RubricCriterion[] \| string` | `{ description, required? }` objects, or a newline-delimited string (list markers stripped). Omit to read a `rubric` value from request context at run time. If none resolves, the scorer returns 1. |
| `options` | `RubricScorerOptions` | Scorer options. |

Returns score `1` only when every required criterion is satisfied, otherwise `0`. `reason` lists each criterion's verdict and is injected as feedback by `isTaskComplete`.

---

## Background subagents and versioning

- Opt subagents into background execution with `backgroundTasks.tools` on the supervisor and keep the stream open with `stream(..., { untilIdle: true, memory })`. `streamUntilIdle()` is deprecated. See `mastra-harness`.
- With the Studio editor, `versions: { agents: { 'research-agent': { status: 'published' }, 'writing-agent': { versionId: '...' } } }` selects stored subagent versions per call. See `mastra-studio-editor`.

---

## agent.network() (deprecated)

`agent.network(messages, options)` still exists but is deprecated. Options include `maxSteps`, `abortSignal`, `onAbort`, `memory`, `structuredOutput`, `modelSettings`, `requestContext`, `tracingOptions`, `onStepFinish`, `onError`. It returns a stream with `status`, `result`, `usage`, `object`, `objectStream`.

Migration: keep the same `agents`, `workflows`, `tools`, and `memory`. Call `stream()` or `generate()` with `maxSteps`, add subagent descriptions, and map events:

| `.network()` event | Supervisor chunk |
|---|---|
| `routing-agent-start` | `step-start` |
| `routing-agent-end` | `step-finish` |
| `agent-execution-start` | `step-start` (when delegating) |
| `agent-execution-event-text-delta` | `text-delta` |
| `agent-execution-event-finish` | `step-finish` |
| `network-execution-event-step-finish` | `step-finish` with `finishReason: 'stop'` |
| `network-object` | `object-delta` (with `structuredOutput`) |
| `network-object-result` | `object` (with `structuredOutput`) |
