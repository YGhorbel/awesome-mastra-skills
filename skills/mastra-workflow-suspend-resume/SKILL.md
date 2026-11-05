---
name: mastra-workflow-suspend-resume
description: "Pause and continue Mastra workflow runs: suspend() inside a step, resumeSchema and suspendSchema, run.resume and resumeStream, human-in-the-loop approvals with bail for rejection, resuming by run ID after a restart, foreach iteration resume, workflow snapshots in storage, the workflow state reader, run statuses, restart of active runs, and time travel to re-run from any step. Use this skill whenever a workflow must wait for a person, a webhook, an external job, or a timer, or when the user needs to recover, inspect, retry, or debug a stored run. Triggers on suspend, resume, resumeData, suspendData, suspendPayload, result.suspended, run.resume, resumeStream, forEachIndex, resumeLabel, createWorkflowStateReader, getWorkflowRunById, loadWorkflowSnapshot, workflow_snapshots, timeTravel, timeTravelStream, restart, WORKFLOW_RESUME_ALREADY_CLAIMED, approval step, human approval in a workflow. Also triggers for long-running or multi-day processes built with Mastra workflows."
license: Apache-2.0
metadata:
  category: workflows
  catalog_summary: "Suspend and resume, human-in-the-loop steps, snapshots, state reader, run status, restart, and time travel"
  display_order: 2
  docs: https://mastra.ai/docs/workflows/suspend-and-resume
---

# Mastra Workflow Suspend and Resume

Pause a workflow inside a step, persist its snapshot, and continue it later with typed resume data. Use the same snapshots to recover runs, inspect them, and re-execute from any step with time travel.

---

## When to use

- A step needs a human decision (approve, reject, edit) before continuing
- A step waits for an external event: webhook, payment callback, batch job, file upload
- Multi-stage approvals where each stage suspends in turn
- Resuming a run from an HTTP handler or a different process using only its `runId`
- Approving `.foreach()` items one at a time
- Inspecting a stored run, finding which step is suspended, and why
- Re-running a failed step with corrected input (time travel)
- Restarting runs that were active when a server died

## When NOT to use

- Building the workflow graph, schemas, and control flow (use `mastra-workflows`)
- Approving an agent's tool calls, or agent-level human-in-the-loop (use `mastra-agent-approval-hitl`)
- Choosing and configuring a storage adapter (use `mastra-storage`)
- Fixed delays without a step context (`.sleep()` and `.sleepUntil()` are covered in `mastra-workflows`)
- Durable agents and background tasks (use `mastra-harness`)
- Resuming runs from a frontend over HTTP (use `mastra-client-sdk`)

---

## Required inputs

- Which step pauses and what it waits for
- The payload shown to whoever resumes it (`suspendSchema`)
- The data needed to continue (`resumeSchema`)
- What happens on rejection: bail with success, throw, or branch
- The storage adapter (snapshots must outlive the process in production)
- Who resumes the run and how they get the `runId` (UI, webhook, queue)

---

## The framework: suspend, persist, resume

A step suspends by returning `suspend(payload)`. Mastra writes a snapshot to storage and the run returns `status: 'suspended'`. Later, `run.resume({ step, resumeData })` reloads the snapshot and re-executes that step with `resumeData` set.

```typescript
// src/mastra/workflows/approval-workflow.ts
import { createStep, createWorkflow } from '@mastra/core/workflows'
import { z } from 'zod'

export const approvalStep = createStep({
  id: 'approval-step',
  inputSchema: z.object({ requestId: z.string() }),
  outputSchema: z.object({ result: z.string() }),
  suspendSchema: z.object({ reason: z.string() }),
  resumeSchema: z.object({ approved: z.boolean() }),
  execute: async ({ inputData, resumeData, suspend, bail }) => {
    const { approved } = resumeData ?? {}
    if (approved === false) return bail({ result: 'Rejected' })
    if (!approved) {
      return await suspend({ reason: `Request ${inputData.requestId} needs approval` })
    }
    return { result: `Request ${inputData.requestId} approved` }
  },
})

export const approvalWorkflow = createWorkflow({
  id: 'approval-workflow',
  inputSchema: z.object({ requestId: z.string() }),
  outputSchema: z.object({ result: z.string() }),
})
  .then(approvalStep)
  .commit()
```

```typescript
const workflow = mastra.getWorkflow('approvalWorkflow')
const run = await workflow.createRun()
const result = await run.start({ inputData: { requestId: 'r-42' } })

if (result.status === 'suspended') {
  const path = result.suspended[0] // e.g. ['approval-step']
  console.log(result.steps[path[0]].suspendPayload) // { reason: '...' }

  // later, possibly in another process:
  const resumed = await run.resume({ step: approvalStep, resumeData: { approved: true } })
}
```

Execute params on resume:

| Param | First run | After resume |
|---|---|---|
| `resumeData` | `undefined` | Typed by `resumeSchema` |
| `suspendData` | `undefined` | The payload passed to `suspend()` |
| `state` | Current state | State saved before the suspend |

`step` accepts a step object (typed `resumeData`), a step ID, or a path array. Omit it only when exactly one step is suspended.

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/` and the installed `Run` types. Otherwise fetch `https://mastra.ai/docs/workflows/suspend-and-resume.md`, `https://mastra.ai/reference/workflows/run-methods/resume.md`, and `https://mastra.ai/docs/workflows/time-travel.md`. Trust these over memory.
2. **Configure storage.** Add a persistent adapter to `new Mastra({ storage })` (for example `LibSQLStore` with `url: 'file:./mastra.db'`). In-memory storage loses suspended runs on restart.
3. **Design the pause.** Write `suspendSchema` (what the reviewer sees) and `resumeSchema` (what they send back). Keep both small and JSON-serializable.
4. **Write the suspend condition.** Read `resumeData ?? {}`. Handle rejection first (`bail()`), then suspend when input is missing, then continue.
5. **Expose the pause.** Persist or return `runId` and `suspendPayload` to the UI, ticket, or message that collects the decision.
6. **Resume.** Rebuild the run with `workflow.createRun({ runId })`, then call `run.resume({ step, resumeData })`. Catch `WORKFLOW_RESUME_ALREADY_CLAIMED` for double-clicks and retried webhooks.
7. **Recover and inspect.** Use `workflow.getWorkflowRunById(runId)` with `createWorkflowStateReader()` to find suspended steps and resume labels.
8. **Debug with time travel.** Re-run from a step with `run.timeTravel({ step, inputData })` once the cause is fixed.
9. **Test** each path: suspend, approve, reject, double resume, resume after restart.

---

## Deep dive: resuming later and recovering runs

Resume from anywhere with only the `runId`:

```typescript
import { createWorkflowStateReader } from '@mastra/core/workflows'

const workflow = mastra.getWorkflow('approvalWorkflow')
const state = await workflow.getWorkflowRunById(runId)

if (state?.status === 'suspended') {
  const reader = createWorkflowStateReader(state)
  const suspendedStep = reader.getSuspendedStep()
  const label = reader.getResumeLabel('approve')

  const run = await workflow.createRun({ runId: state.runId })
  try {
    await run.resume({
      step: label?.stepId ?? suspendedStep?.path,
      resumeData: { approved: true },
      forEachIndex: label?.foreachIndex,
    })
  } catch (error) {
    if (error.id === 'WORKFLOW_RESUME_ALREADY_CLAIMED') {
      // Another caller is continuing this run. Re-read state instead.
    }
  }
}
```

- Name a pause with `suspend(payload, { resumeLabel: 'approve' })` so callers can find it by label.
- In `.foreach()`, each iteration suspends on its own. Pass `forEachIndex` (zero-based) to resume one item. Omit it to resume all with the same data.
- Nested workflows report paths such as `['nested-workflow', 'step-1']`. Pass the whole path as `step`.
- With `run.stream()`, the stream closes on suspend by default (`closeOnSuspend: true`). Continue with `run.resumeStream({ resumeData })`.
- `.sleep()` sets status `waiting`; `suspend()` sets `suspended`. Only suspended steps take `resumeData`.

---

## Failure patterns

- **No storage or `:memory:` storage in production.** Suspended runs vanish on restart. Use a persistent adapter.
- **`resumeData.approved` without a fallback.** `resumeData` is `undefined` on the first run. Destructure from `resumeData ?? {}`.
- **Treating `false` and `undefined` the same.** A rejection then suspends again forever. Check `approved === false` before `!approved`.
- **Forgetting `return` before `suspend()`.** Code after it runs. Write `return await suspend({...})`.
- **Resuming with a fresh `createRun()`.** That creates a new run. Pass `{ runId }` from the suspended run.
- **Omitting `step` with several suspended steps.** Resume fails. Pass the step, ID, or path from `result.suspended`.
- **Reading `result.suspended[0]` as a string.** Each entry is a path array. Use `result.steps[path[0]]` for the payload.
- **Double resume from a retried webhook.** The second call throws `WORKFLOW_RESUME_ALREADY_CLAIMED` (HTTP 409). Catch it and re-read state. Adapters without atomic updates (ClickHouse, Cloudflare D1, KV, Durable Objects, LanceDB, Redis) cannot enforce this claim.
- **Large objects in `suspend()` payloads.** Snapshots bloat. Store IDs and fetch data on resume.
- **Time travel on a running run.** It throws (`WORKFLOW_TIME_TRAVEL_RUN_RUNNING`). Wait for the run to finish or suspend.
- **Time travel after renaming steps.** It fails before running anything. Keep step IDs stable.

---

## Output format

A finished suspend and resume delivery contains:

- Steps with `suspendSchema`, `resumeSchema`, and a rejection path
- Persistent `storage` on the `Mastra` instance
- A resume entry point (route, webhook handler, or job) that rebuilds the run by `runId` and handles the already-claimed error
- A way to show `suspendPayload` to the person or system that resumes
- Tests or Studio runs for approve, reject, double resume, and resume after restart

---

## Reference files

- [`references/api.md`](references/api.md) - `suspend()`, resume and stream options, run statuses, snapshot anatomy, state reader functions, restart, time travel parameters and errors.
- [`references/examples.md`](references/examples.md) - Approval endpoint with resume by run ID, multi-stage approvals, per-item foreach approval, recovering a failed run with time travel.
- [`references/checklist.md`](references/checklist.md) - Production checklist for pausable workflows.

**Live docs**

- https://mastra.ai/docs/workflows/suspend-and-resume
- https://mastra.ai/docs/workflows/human-in-the-loop
- https://mastra.ai/docs/workflows/snapshots
- https://mastra.ai/docs/workflows/time-travel
- https://mastra.ai/reference/workflows/run-methods/resume
- https://mastra.ai/reference/workflows/run-methods/timeTravel
- https://mastra.ai/reference/workflows/workflow-state-reader
- https://mastra.ai/reference/streaming/workflows/resumeStream
