# Workflow API reference

Distilled from `https://mastra.ai/reference/workflows/workflow.md`, `step.md`, `run.md`, `workflow-methods/*`, `run-methods/*`, `https://mastra.ai/reference/streaming/workflows/stream.md`, and the workflow docs pages. Verify against the installed version before relying on an option.

## Contents

- `createWorkflow()` options
- `createStep()` options
- Execute params
- Steps from agents, tools, and classifiers
- Control-flow methods
- `createRun()` and `Run` methods
- Start and stream options
- Result and status values
- Stream events
- Workflow instance methods
- Dynamic workflows

---

## `createWorkflow()` options

Import: `import { createWorkflow, createStep, cloneWorkflow, mapVariable } from '@mastra/core/workflows'`

| Option | Notes |
|---|---|
| `id` | Required. Unique workflow ID. |
| `inputSchema` / `outputSchema` | Standard JSON Schema (Zod, Valibot via `toStandardJsonSchema`, ArkType). |
| `stateSchema` | Master schema for shared state. |
| `requestContextSchema` | Validates request context at `run.start()`. |
| `retryConfig` | `{ attempts, delay }`. Default retries for every step (from the error handling guide). |
| `schedule` | Cron config, see `mastra-schedules`. |
| `options.validateInputs` | Validate input, resume data, and step input. Applies schema defaults. |
| `options.onStart(info)` | Awaited before the first step. Throwing rejects `start()`/`stream()`. Not called on resume, restart, or time travel. |
| `options.onFinish(result)` | Any final status. Receives `status`, `result`, `error`, `steps`, `tripwire`, `runId`, `workflowId`, `resourceId`, `getInitData`, `mastra`, `requestContext`, `logger`, `state`. Errors are logged, not thrown. |
| `options.onError(info)` | Only `failed` or `tripwire`. Same fields. Errors are logged. |
| `options.autoRestartActiveRuns` | `false` opts out of boot-time restart of active runs. |
| `options.shouldPersistSnapshot` | `({ stepResults, workflowStatus }) => boolean`. |
| `options.pruneSnapshot` | Transform the snapshot before persisting. Must keep resume data. |
| `options.storageVersion` | Experimental `1 \| 2`. Version 2 saves deltas, in-memory storage and default engine only. |
| `options.tracingPolicy` | Tracing policy. |

`cloneWorkflow(workflow, { id })` copies a workflow under a new ID.

---

## `createStep()` options

| Option | Notes |
|---|---|
| `id` | Required. Becomes the key in parallel and branch outputs and in `result.steps`. |
| `description` | Optional. |
| `inputSchema` / `outputSchema` | Required for typed chaining. |
| `stateSchema` | Subset of the workflow `stateSchema`. |
| `resumeSchema` / `suspendSchema` | See `mastra-workflow-suspend-resume`. |
| `requestContextSchema` | Validated before `execute`. Fails the step on mismatch. |
| `execute` | `async (params) => output`. |
| `retries` | Retries when `execute` throws. Overrides `retryConfig`. |
| `scorers` | `{ name: { scorer, sampling? } }` or a function. Runs async after success. |
| `metadata` | Serializable key-value pairs. |

---

## Execute params

| Param | Notes |
|---|---|
| `inputData` | Typed by `inputSchema`. |
| `mastra` | Mastra instance: `mastra.getAgent('key')`, `mastra.getAgentById(id)`. |
| `state`, `setState` | Shared state. `setState` follows a reducer pattern: `setState({ ...state, ...changes })`. |
| `getStepResultAsync(stepOrId)` | Output of another step, or `null` if it did not succeed. |
| `getStepResult(stepOrId)` | Deprecated synchronous version. |
| `getInitData()` | Workflow input. |
| `requestContext` | `RequestContext` for the run. |
| `runId` | Current run ID. |
| `retryCount` | Current retry attempt for this step. |
| `bail(payload)` | End the workflow early with `success` and `payload` as the result. |
| `abortSignal`, `abort()` | Respond to `run.cancel()`. |
| `writer` | Stream custom output. `await stream.textStream.pipeTo(writer)` pipes an agent and aggregates its usage. |
| `suspend`, `resumeData`, `suspendData` | See `mastra-workflow-suspend-resume`. |

---

## Steps from agents, tools, and classifiers

| Call | Input | Output |
|---|---|---|
| `createStep(agent)` | `{ prompt: string }` | `{ text: string }` |
| `createStep(agent, { structuredOutput: { schema }, onFinish })` | `{ prompt: string }` | `schema` |
| `.agent(agentOrId, options?, { id? })` | `{ prompt: string }` | `{ text }` or `structuredOutput.schema` |
| `createStep(tool)` / `.tool(toolOrId, { retries?, scorers?, metadata? }, { id? })` | Tool `inputSchema` | Tool `outputSchema` |
| `createStep(classifier, { maxRetries, retries })` / `.classifier(classifier)` | Full `inputData` | `{ answers, usage }` |

`.agent()` options accept agent call options (`maxSteps`, `modelSettings`, `memory`, `providerOptions`) plus `structuredOutput`, `retries`, `scorers`, `metadata`. Only `structuredOutput.schema`, `retries`, and `metadata` survive storage. Pass `{ id }` as the third argument when the same agent or tool appears twice.

Calling a tool inside `execute`: `await testTool.execute?.(input, { requestContext })`, then check `isValidationError(response)` from `@mastra/core/tools`.

---

## Control-flow methods

Every method returns the workflow for chaining. Most accept a final `StepFlowEntryOptions` (`{ id, description, metadata }`) that labels the graph entry without changing execution.

| Method | Signature notes |
|---|---|
| `.then(step)` | Sequential. |
| `.parallel(steps, opts?)` | Output keyed by step ID. No concurrency limit. |
| `.branch([[condition, step], ...], opts?)` | Condition is `async ({ inputData, ... }) => boolean` or `{ predicate }`. All true conditions run. |
| `.dountil(step, condition, opts?)` | Runs at least once. Condition receives execute params (minus `setState`, `suspend`) plus `iterationCount` (starts at 1). Ends when true. |
| `.dowhile(step, condition, opts?)` | Repeats while true. |
| `.foreach(step, { concurrency?, id?, description?, metadata? })` | Previous output must be an array. Default concurrency 1. Emits `workflow-step-progress`. |
| `.map(fn \| object, opts?)` | `fn({ inputData, getStepResultAsync, getInitData, ... })`. Object form uses `mapVariable({ step, path })` or `mapVariable({ initData: workflow, path })`, or `{ initData: true, path }`. |
| `.sleep(ms \| fn, opts?)` | `fn({ inputData })` returns milliseconds. |
| `.sleepUntil(date \| fn, opts?)` | `fn` returns a `Date`. |
| `.agent()`, `.tool()`, `.classifier()` | Declarative steps. |
| `.commit()` | Finalize. Required before `createRun()`. |

---

## `createRun()` and `Run` methods

`const run = await workflow.createRun({ runId?, resourceId?, disableScorers? })`

| Method | Returns | Notes |
|---|---|---|
| `start(opts)` | `Promise<WorkflowResult>` | Waits for completion. |
| `startAsync(opts)` | `Promise<{ runId }>` | Fire and forget. Poll `workflow.getWorkflowRunExecutionResult(runId)`. |
| `stream(opts)` | `WorkflowRunOutput` | Iterate it or `.fullStream`. `.result`, `.usage`, `.status`. |
| `resume(opts)` / `resumeStream(opts)` | Result or stream | See `mastra-workflow-suspend-resume`. |
| `observeStream()` | `ReadableStream` | Reattach to a running run's events. |
| `cancel()` | `Promise<void>` | Triggers `abortSignal`, stops later steps. Cancels nested runs. |
| `restart(opts?)` | `Promise<WorkflowResult>` | Continue an active run that lost its process. Throws `WORKFLOW_RESTART_RUN_OWNED` while another process holds the lease. |
| `timeTravel(opts)` / `timeTravelStream(opts)` | Result or stream | See `mastra-workflow-suspend-resume`. |

---

## Start and stream options

| Option | Notes |
|---|---|
| `inputData` | Matches workflow `inputSchema`. |
| `initialState` | Matches `stateSchema`. |
| `requestContext` | `RequestContext` instance. |
| `tracingOptions` | `{ rootSpanName, metadata, tags, requestContextKeys, traceId, parentSpanId, nestUnderParent }`. |
| `outputOptions.includeState` | Include state in the result. |
| `outputWriter` | `start()` only. Async handler for output chunks. |
| `closeOnSuspend` | `stream()` only. Default `true`. |

---

## Result and status values

`result.status`, `result.input`, `result.steps`, and optional `result.state` are always present.

| Status | Extra fields |
|---|---|
| `success` | `result` |
| `failed` | `error` |
| `suspended` | `suspendPayload`, `suspended` (array of step paths) |
| `tripwire` | `tripwire: { reason, retry?, metadata?, processorId? }` |
| `paused` | none (per-step execution) |

Stored run statuses also include `pending`, `running`, `waiting` (sleeping or interrupted), `canceled`, `bailed`, and `skipped`. Each `result.steps[id]` has `status`, `payload`, `output`, and `error` when failed.

---

## Stream events

| Event `type` | Payload notes |
|---|---|
| `workflow-start` | Run started. |
| `workflow-step-start` | Step started. |
| `workflow-step-output` | Custom output written to `writer`. |
| `workflow-step-progress` | Foreach: `id`, `completedCount`, `totalCount`, `currentIndex`, `iterationStatus`, `iterationOutput`. |
| `workflow-step-result` | Step finished. |
| `workflow-finish` | Usage stats. `payload.finalWorkflowResult` on success. |

---

## Workflow instance methods

| Method | Notes |
|---|---|
| `mastra.getWorkflow(key)` | By registration key, with type inference. Preferred. |
| `mastra.getWorkflowById(id)` | By workflow `id`, weaker typing. |
| `workflow.getWorkflowRunById(runId)` | Stored run state, including `resourceId`. |
| `workflow.getWorkflowRunExecutionResult(runId)` | Status and step outputs for `startAsync` runs. |
| `workflow.listActiveWorkflowRuns()` | `{ runs }` with status `running` or `waiting`. |
| `workflow.restartAllActiveWorkflowRuns()` | Restart active runs, up to `recovery.workflowConcurrency` (default 5) at once. |

---

## Dynamic workflows (beta)

| API | Notes |
|---|---|
| `mastra.addDynamicWorkflow(definition)` | Validates, registers, and persists a JSON definition. Same `id` replaces it for new runs. |
| `mastra.addDynamicWorkflows([root, ...helpers])` | Validates a bundle as a unit and orders by dependency. |
| Definition fields | `id`, `description`, `inputSchema` and `outputSchema` as JSON Schema, `graph` entries. |
| Graph entry types | Agent, classifier, tool (`{ type: 'tool', id, toolId }`), mapping, nested workflow, parallel, conditional, foreach, loop, sleep. |
| Persistence | `workflowDefinitions` storage domain. Without support, definitions live in memory only. |
| HTTP | `POST /api/stored/workflows` or client `upsertDynamicWorkflow()`. Needs `stored-workflows:read`/`write` permissions. |

Register referenced agents, tools, and workflows on the same `Mastra` instance first. A tool entry uses the tool's key in `new Mastra({ tools })`. See `https://mastra.ai/reference/workflows/dynamic-workflow-definition.md` for every graph field.
