# Workflow checklist

Run this before calling a workflow done.

## Definition

- [ ] Workflow and every step have stable kebab-case `id` values (step IDs key parallel and branch outputs, `result.steps`, and resume targets)
- [ ] First step input matches the workflow `inputSchema`; last step output matches the workflow `outputSchema`
- [ ] Every step boundary matches, or a `.map()` reshapes the data
- [ ] Steps after `.parallel()` and `.branch()` accept the keyed output shape, with `.optional()` for branch keys
- [ ] Branch conditions are mutually exclusive unless several paths should run
- [ ] Loops have an exit condition and an `iterationCount` guard
- [ ] `.foreach()` has an explicit `concurrency` for I/O-bound work
- [ ] The chain ends with `.commit()`

## Data and state

- [ ] Values that many steps need live in `stateSchema` instead of being threaded through every schema
- [ ] `initialState` passed on `run.start()` when the workflow has a `stateSchema`
- [ ] Step outputs are JSON-serializable and small (store IDs, not large blobs)
- [ ] `getStepResultAsync()` used instead of the deprecated `getStepResult()`

## Resilience

- [ ] Steps that call networks or LLMs have `retries` or the workflow has `retryConfig`
- [ ] Parallel steps that may fail catch errors and return a typed failure result
- [ ] Early exits use `bail()`; real failures throw
- [ ] `onError` alerts or logs; critical side effects live in steps, not callbacks
- [ ] Long steps check `abortSignal` so `run.cancel()` can stop them

## Wiring

- [ ] Registered in `new Mastra({ workflows })`
- [ ] Callers use `mastra.getWorkflow('key')`
- [ ] Storage configured if runs must persist, restart, or be inspected later (see `mastra-storage`)
- [ ] Agents and tools referenced by ID are registered on the same `Mastra` instance

## Testing

- [ ] Run once in Studio or with `npx mastra api workflow run start`
- [ ] Callers handle every `result.status`: `success`, `failed`, `suspended`, `tripwire`, `paused`
- [ ] A trace reviewed for slow or retried steps (see `mastra-observability`)
