# Suspend and resume checklist

Run this before calling a pausable workflow done.

## Step design

- [ ] Every suspending step has a `suspendSchema` (what the reviewer sees) and a `resumeSchema` (what they send back)
- [ ] `resumeData` is read as `resumeData ?? {}`
- [ ] Rejection (`=== false`) is handled before the suspend check, usually with `bail()`
- [ ] `suspend()` is returned: `return await suspend({...})`
- [ ] Suspend payloads hold IDs and short text, not large objects
- [ ] Pauses that callers look up by name use `suspend(payload, { resumeLabel })`
- [ ] Step IDs are stable (resume targets and time travel depend on them)

## Persistence

- [ ] `new Mastra({ storage })` uses a persistent adapter, not `:memory:`
- [ ] The adapter supports atomic claims if several processes or retried webhooks can resume the same run
- [ ] `runId` is stored with the business record (ticket, order, request) that the reviewer acts on

## Resume path

- [ ] The resume handler rebuilds the run with `workflow.createRun({ runId })`
- [ ] It passes `step` explicitly when more than one step can be suspended
- [ ] It catches `WORKFLOW_RESUME_ALREADY_CLAIMED` (HTTP 409) and re-reads state
- [ ] `.foreach()` approvals pass `forEachIndex` per item
- [ ] Streaming callers continue with `resumeStream()` after a suspend closes the stream
- [ ] Authorization checks who may resume (see `mastra-auth`)

## Recovery and debugging

- [ ] A job or dashboard lists suspended runs with `getWorkflowRunById` and `createWorkflowStateReader`
- [ ] Side-effecting steps are idempotent, since restart and recovery may re-run a step
- [ ] Time travel used for re-running failed steps after a fix, with storage configured

## Tests

- [ ] Suspend, approve, reject, double resume, and resume after a process restart are covered
- [ ] Callers handle `suspended` and `waiting` as non-final statuses
