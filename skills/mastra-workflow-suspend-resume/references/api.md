# Suspend, resume, and time travel API reference

Distilled from `https://mastra.ai/docs/workflows/suspend-and-resume.md`, `human-in-the-loop.md`, `snapshots.md`, `time-travel.md`, `https://mastra.ai/reference/workflows/step.md`, `run.md`, `run-methods/resume.md`, `run-methods/restart.md`, `run-methods/timeTravel.md`, `workflow-state-reader.md`, and `https://mastra.ai/reference/streaming/workflows/resumeStream.md`. Verify against the installed version before relying on an option.

## Contents

- Step fields for suspension
- `run.resume()` options
- `run.resumeStream()`
- Result and run statuses
- Concurrency claims
- Snapshots
- Workflow state reader
- `run.restart()` and active runs
- `run.timeTravel()` and `timeTravelStream()`

---

## Step fields for suspension

| Field / param | Notes |
|---|---|
| `suspendSchema` | Schema of the payload passed to `suspend()`. |
| `resumeSchema` | Schema of `resumeData`. |
| `suspend(payload, { resumeLabel? })` | Pauses the step. Return it: `return await suspend({...})`. |
| `resumeData` | `undefined` on first execution. Typed by `resumeSchema` after resume. |
| `suspendData` | The original `suspend()` payload, available after resume. |
| `bail(payload)` | Ends the run with `success` and `payload` as result. Use for rejections. |
| `state`, `setState` | State changes made before a suspend persist through resume. |

---

## `run.resume()` options

`const run = await workflow.createRun({ runId })` reattaches to an existing run.

| Option | Notes |
|---|---|
| `resumeData` | Matches the step's `resumeSchema`. |
| `step` | Step object, step ID, array of steps, or array of IDs (nested path). Optional when exactly one step is suspended. |
| `forEachIndex` | Zero-based `.foreach()` iteration to resume. Omit to resume all suspended iterations with the same data. |
| `requestContext` | `RequestContext` for the resumed execution. |
| `retryCount` | Retry count for nested workflow execution. |
| `tracingOptions`, `tracingContext` | Same shape as `start()`. |
| `outputOptions.includeState` | Include state in the result. |

Returns `Promise<WorkflowResult>` plus `traceId` and `spanId` when tracing is on. A resumed run may suspend again at a later step; resume each stage in sequence.

---

## `run.resumeStream()`

Same options as `resume()` (`resumeData`, `step`, `forEachIndex`, `requestContext`, `tracingOptions`). Returns a `MastraWorkflowStream` with `status`, `result`, and `usage` promises. Called with no arguments, `run.resumeStream()` reopens an interrupted stream. `run.stream()` closes on suspend by default (`closeOnSuspend: true`).

---

## Result and run statuses

On `status: 'suspended'` the result has:

| Field | Notes |
|---|---|
| `suspended` | Array of suspended paths, each a `string[]` such as `['nested-workflow', 'step-1']`. |
| `suspendPayload` | Suspension data. |
| `steps[stepId].suspendPayload` | Payload of one suspended step. |

Run statuses:

| Status | Meaning |
|---|---|
| `pending` | Created, not started. |
| `running` | Executing. |
| `waiting` | Sleeping (`.sleep()`/`.sleepUntil()`) or interrupted before finishing. |
| `suspended` | Paused by `suspend()`, waiting for resume. |
| `success` | Finished with output. |
| `failed` | Finished with an error. |
| `tripwire` | Stopped by a processor tripwire. |
| `paused` | Stopped after one step in per-step execution. |
| `canceled` | Stopped by `run.cancel()`. |
| `bailed` | A step called `bail()`. The run completes as `success`. |
| `skipped` | Step not executed, for example a false branch. |

---

## Concurrency claims

| Call | Losing caller gets | HTTP |
|---|---|---|
| `resume()` | `WORKFLOW_RESUME_ALREADY_CLAIMED` (error `id`) | `409 Conflict` |
| `timeTravel()` | `WORKFLOW_TIME_TRAVEL_ALREADY_CLAIMED`, or `WORKFLOW_TIME_TRAVEL_RUN_RUNNING` if the run is executing | `409` on `time-travel-async` only |
| `restart()` | `WORKFLOW_RESTART_RUN_OWNED` while another process holds the lease | n/a |

Claims are atomic only on adapters that report `supportsConcurrentUpdates()`. ClickHouse, Cloudflare D1, Cloudflare KV, Cloudflare Durable Objects, LanceDB, and Redis cannot enforce them. Claims are also skipped when `shouldPersistSnapshot` excludes `running`.

---

## Snapshots

- Created automatically on suspend and saved to the `workflow_snapshots` table, keyed by `runId`.
- Contain `runId`, `status`, `context` (input plus each step's `payload`, `output`, `suspendPayload`, `resumePayload`, timestamps), `activePaths`, `serializedStepGraph`, `suspendedPaths`, `waitingPaths`, `result`, `requestContext`, `timestamp`.
- Shared across all workflows on one `Mastra` instance's `storage`.

Read one directly:

```typescript
const storage = mastra.getStorage()
const workflowStore = await storage?.getStore('workflows')
const snapshot = await workflowStore?.loadWorkflowSnapshot({
  runId: '<run-id>',
  workflowName: '<workflow-id>',
})
```

Workflow options that affect snapshots: `shouldPersistSnapshot`, `pruneSnapshot`, `storageVersion` (see `mastra-workflows`).

---

## Workflow state reader

Import from `@mastra/core/workflows`. Input is the `WorkflowState` from `workflow.getWorkflowRunById(runId)`.

| Function | Returns |
|---|---|
| `createWorkflowStateReader(state)` | Reader with the methods below. |
| `getWorkflowStepOutput(state, stepId)` | Output; dot paths for nested; array for foreach. |
| `getWorkflowStepPayload(state, stepId)` | Input payload. |
| `getWorkflowSuspendedStep(state)` | First suspended step. |
| `getWorkflowSuspendedSteps(state)` | All suspended steps. |
| `getWorkflowResumeLabel(state, label)` | `{ stepId, foreachIndex? }`. |
| `getWorkflowResumeLabels(state)` | Record of labels. |

Reader methods: `getStatus()`, `getResult()`, `getError()`, `getStepOutput(id)`, `getStepPayload(id)`, `getSuspendedStep()`, `getSuspendedSteps()`, `getResumeLabel(label)`, `getResumeLabels()`. A suspended step entry has `stepId`, `path`, `executionPath`, `step`, `payload`, `suspendPayload`, `suspendOutput`, `resumeLabels`.

`requestContext` and `tracingContext` come back from `getWorkflowRunById()` only when requested with `fields`.

---

## `run.restart()` and active runs

| API | Notes |
|---|---|
| `run.restart({ requestContext?, tracingOptions?, outputOptions? })` | Continues an active run from its last active step after the process lost it. |
| `workflow.listActiveWorkflowRuns()` | `{ runs }` with status `running` or `waiting`. |
| `workflow.restartAllActiveWorkflowRuns()` | Restarts all, skipping runs whose lease has not expired. |
| `mastra.restartAllActiveWorkflowRuns()` | Boot-time sweep. The local server runs it on start. |
| `recovery: { workflows: 'auto' \| 'off', workflowConcurrency }` | `Mastra` config. Default `'auto'`, concurrency 5. |
| `options.autoRestartActiveRuns: false` | Per-workflow opt-out. |

The lease is advisory: a blocked process can let recovery run a step twice. Make side-effecting steps idempotent.

---

## `run.timeTravel()` and `timeTravelStream()`

Requires storage. Can also run a workflow that has never run, starting at any step.

| Option | Notes |
|---|---|
| `step` | Step, ID, `'nested.step'` dot path, array of IDs, or array of steps. |
| `inputData` | Input for the target step. Defaults to snapshot data. |
| `resumeData` | For runs that were suspended. |
| `initialState` | Workflow state to start with. |
| `context` | Step results before the target, keyed by step ID: `{ status, payload, output, startedAt, endedAt, suspendPayload?, resumePayload? }`. |
| `nestedStepsContext` | Same, keyed by nested workflow ID. |
| `requestContext`, `outputWriter`, `tracingOptions`, `outputOptions` | As for `start()`. |

Errors thrown before anything runs:

| Situation | Message or id |
|---|---|
| Run still running | `This workflow run is still running, cannot time travel` / `WORKFLOW_TIME_TRAVEL_RUN_RUNNING` |
| Unknown step | `Cannot time travel to step '<id>': the step does not exist in the current execution graph...` |
| Invalid input with `validateInputs` | `Invalid inputData: ...` |
| Concurrent call | `WORKFLOW_TIME_TRAVEL_ALREADY_CLAIMED` |

`timeTravelStream()` takes the same options and returns `{ fullStream, result, runId, workflowId }`.
