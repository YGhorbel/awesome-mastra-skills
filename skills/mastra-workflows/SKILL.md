---
name: mastra-workflows
description: "Build, compose, register, and run Mastra workflows: createStep and createWorkflow with typed schemas, control flow with .then, .parallel, .branch, .dowhile, .dountil, .foreach, .map, .sleep, nested workflows, agents and tools as steps, shared workflow state, retries and error handling, lifecycle callbacks, dynamic JSON-defined workflows, and running with createRun, start, startAsync, and stream. Use this skill whenever the user wants a fixed multi-step pipeline, fan-out and fan-in, conditional routing, looping, batch processing over an array, or a deterministic process that calls agents or tools in a known order. Triggers on Mastra workflow, @mastra/core/workflows, createWorkflow, createStep, .commit(), run.start, run.stream, createRun, mapVariable, getStepResultAsync, setState, stateSchema, retryConfig, bail, onFinish, onError, addDynamicWorkflow, cloneWorkflow, mastra.getWorkflow. Also triggers when an agent is being asked to follow a strict sequence of steps, which is usually a workflow."
license: Apache-2.0
metadata:
  category: workflows
  catalog_summary: "createWorkflow and createStep, control flow, agents and tools as steps, state, retries, dynamic workflows, running and streaming"
  display_order: 1
  docs: https://mastra.ai/docs/workflows/overview
---

# Mastra Workflows

Define typed steps, chain them into a workflow, register it, and run it. Workflows give you explicit control over order, data flow, branching, loops, and retries when the steps are known in advance.

---

## When to use

- A task has known steps in a known order (ingest, transform, call an agent, save)
- Fan-out and fan-in: run independent steps in parallel, then combine
- Conditional routing on a value or a classifier answer
- Loops until a condition holds, or batch work over an array with a concurrency limit
- Calling agents or tools from deterministic code with typed inputs and outputs
- Sharing progress or counters across steps with workflow state
- Retrying flaky steps, failing fast, or exiting early
- Letting users, editors, or an LLM author workflows as JSON (dynamic workflows)

## When NOT to use

- Pausing for approval, human input, or external callbacks, plus snapshots and time travel (use `mastra-workflow-suspend-resume`)
- Open-ended tasks where the model picks the steps (use `mastra-agents`)
- Defining the tools that a step calls (use `mastra-tools`)
- Cron schedules on workflows (use `mastra-schedules`)
- Streaming UI over workflow events in React (use `mastra-agentic-ui`) or event shapes in depth (use `mastra-streaming`)
- Calling workflows over HTTP from a client app (use `mastra-client-sdk`)
- Storage adapters for persisting runs (use `mastra-storage`)
- Workflow runners such as Inngest and worker processes (use `mastra-deployment`)

---

## Required inputs

- The workflow's input and final output shape
- The ordered list of steps, and which ones can run in parallel or need a condition
- Which steps call agents, tools, or external APIs (these need retries and error handling)
- Whether runs must survive restarts or pause (needs storage, see `mastra-workflow-suspend-resume`)
- How it is triggered: code, HTTP, Studio, CLI, or schedule

---

## The framework: steps, composition, runs

### 1. Define steps

```typescript
// src/mastra/workflows/test-workflow.ts
import { createStep, createWorkflow } from '@mastra/core/workflows'
import { z } from 'zod'

const formatStep = createStep({
  id: 'format-step',
  inputSchema: z.object({ message: z.string() }),
  outputSchema: z.object({ formatted: z.string() }),
  execute: async ({ inputData }) => ({ formatted: inputData.message.toUpperCase() }),
})

const emphasizeStep = createStep({
  id: 'emphasize-step',
  inputSchema: z.object({ formatted: z.string() }),
  outputSchema: z.object({ emphasized: z.string() }),
  execute: async ({ inputData }) => ({ emphasized: `${inputData.formatted}!!!` }),
})
```

### 2. Compose and commit

```typescript
export const testWorkflow = createWorkflow({
  id: 'test-workflow',
  inputSchema: z.object({ message: z.string() }),
  outputSchema: z.object({ emphasized: z.string() }),
})
  .then(formatStep)
  .then(emphasizeStep)
  .commit()
```

Schema rules: the first step's `inputSchema` matches the workflow's `inputSchema`, each step's `outputSchema` matches the next step's `inputSchema`, and the last step's `outputSchema` matches the workflow's `outputSchema`. Use `.map()` where they differ. Schemas can be Zod, Valibot (through `toStandardJsonSchema`), ArkType, or any Standard JSON Schema.

### 3. Register and run

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { testWorkflow } from './workflows/test-workflow'

export const mastra = new Mastra({ workflows: { testWorkflow } })
```

```typescript
const workflow = mastra.getWorkflow('testWorkflow') // registration key, full type inference
const run = await workflow.createRun()
const result = await run.start({ inputData: { message: 'Hello world' } })

if (result.status === 'success') console.log(result.result)
else if (result.status === 'failed') console.error(result.error.message)
```

### Control flow at a glance

| Method | Input to next step | Notes |
|---|---|---|
| `.then(step)` | That step's output | Sequential |
| `.parallel([a, b])` | `{ 'a-id': outA, 'b-id': outB }` | All run, all must finish |
| `.branch([[cond, step], ...])` | `{ 'step-id': out }` for each true condition | Every true condition runs |
| `.dountil(step, cond)` / `.dowhile(step, cond)` | Last iteration output | Condition gets `iterationCount` |
| `.foreach(step, { concurrency })` | Array of outputs, input order | Default concurrency 1 |
| `.map(fn \| { field: mapVariable(...) })` | Mapped object | Reshape between steps |
| `.sleep(ms)` / `.sleepUntil(date)` | Unchanged | Run status becomes `waiting` |
| `.agent(agent)` / `.tool(tool)` | `{ text }` or tool output | Declarative, serializable steps |

A committed workflow can also be a step inside another workflow (`.then(childWorkflow)`, `.foreach(childWorkflow)`, `.parallel([wfA, wfB])`).

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/` and the installed `createWorkflow` and `createStep` types. Otherwise fetch `https://mastra.ai/docs/workflows/overview.md`, `https://mastra.ai/docs/workflows/control-flow.md`, and `https://mastra.ai/reference/workflows/step.md`. Trust these over memory.
2. **Sketch the graph.** List steps, mark parallel groups, branches, loops, and array fan-out. Decide which values travel as step I/O and which belong in workflow state.
3. **Write schemas first.** One schema per step boundary. Reuse schema constants across steps to keep shapes in sync. Remember parallel and branch outputs are keyed by step `id`.
4. **Write steps.** Give every step a stable kebab-case `id`. Keep `execute` small. Use `mastra` from the execute params to reach registered agents (`mastra.getAgent('key')`).
5. **Compose and `.commit()`.** Add `.map()` wherever shapes differ.
6. **Add resilience.** `retryConfig` on the workflow, `retries` on flaky steps, `try/catch` inside steps whose failure should not fail a parallel block, `bail()` for early success exits, `onError` for alerts.
7. **Register** the workflow in `new Mastra({ workflows })` and add `storage` if runs must persist.
8. **Run and test.** Use Studio (`npx mastra dev`, Workflows tab) or `npx mastra api workflow run start <workflow-id> '{"inputData":{...}}'` against a running server. Check every `result.status` branch.

---

## Deep dive: agents, tools, and state

Agents as steps take `{ prompt: string }` and return `{ text: string }` unless you pass `structuredOutput`:

```typescript
import { createStep } from '@mastra/core/workflows'
import { z } from 'zod'
import { testAgent } from '../agents/test-agent'

const articleSchema = z.object({ title: z.string(), summary: z.string(), tags: z.array(z.string()) })
const writeArticle = createStep(testAgent, { structuredOutput: { schema: articleSchema } })

// .map(async ({ inputData }) => ({ prompt: `Write about: ${inputData.topic}` })).then(writeArticle)
```

Tools as steps keep the tool's own schemas: `createStep(testTool)` or `.tool(testTool)`. Calling an agent inside `execute` gives more control (memory, options, streaming into `writer`).

Workflow state shares values without threading them through every schema. Declare the full `stateSchema` on the workflow, the subset each step needs on the step, and pass `initialState` to `run.start()`:

```typescript
execute: async ({ inputData, state, setState }) => {
  await setState({ ...state, processedItems: [...state.processedItems, inputData.id] })
  return { ok: true }
}
```

State persists across suspend and resume and propagates into nested workflows.

---

## Failure patterns

- **Forgetting `.commit()`.** Creating a run on uncommitted steps throws. End every chain with `.commit()`.
- **Next step expects a flat object after `.parallel()` or `.branch()`.** Output is keyed by step `id`. Match that shape or `.map()` it.
- **Overlapping branch conditions.** Every true condition runs. Make conditions mutually exclusive, and do not end with an unconditional `true` fallback unless it should also run.
- **Missing optional fields after `.branch()`.** The next step must accept every branch's output. Mark branch keys `.optional()`.
- **Chained `.foreach().foreach()` producing arrays of arrays.** Use a nested workflow per item, or `.map(({ inputData }) => inputData.flat())`.
- **Infinite loops.** Guard `.dountil()`/`.dowhile()` with `iterationCount` and throw past a limit.
- **Values dropped between loop iterations.** Object schemas strip undeclared keys. Declare carried values in the loop body's `inputSchema` or use state.
- **One failing parallel step fails the whole block.** Catch inside the step and return a typed `{ failed: true }` result.
- **Importing the workflow directly to run it.** Use `mastra.getWorkflow('key')` for storage, logger, registered agents, and type inference.
- **`getStepResult()` in new code.** It is deprecated. Use `await getStepResultAsync(step)`.
- **Reading `result.result` without checking `result.status`.** Only `success` has `result`. Handle `failed`, `suspended`, `tripwire`, and `paused`.
- **Lifecycle callbacks for critical work.** `onFinish` and `onError` are not durable or retried, and their errors are only logged. Put must-run work in a step.

---

## Output format

A finished workflow delivery contains:

- `src/mastra/workflows/<workflow-id>.ts` exporting the committed workflow and its steps
- Registration in `src/mastra/index.ts` (plus `storage` if runs persist)
- Env vars for any agents or services in `.env.example`
- A run snippet (`createRun` + `start` or `stream`) with handling for each `result.status`
- Evidence: a Studio run, a `mastra api workflow run start` call, or a test asserting the output

---

## Reference files

- [`references/api.md`](references/api.md) - `createWorkflow`, `createStep`, execute params, control-flow methods, `Run` methods, result and status values, stream events, dynamic workflow API.
- [`references/examples.md`](references/examples.md) - Parallel plus branch routing, agent pipeline with structured output, batch foreach with nested workflow and state, streaming with retries and callbacks.
- [`references/checklist.md`](references/checklist.md) - Pre-production checklist for a workflow.

**Live docs**

- https://mastra.ai/docs/workflows/overview
- https://mastra.ai/docs/workflows/control-flow
- https://mastra.ai/docs/workflows/agents-and-tools
- https://mastra.ai/docs/workflows/workflow-state
- https://mastra.ai/docs/workflows/error-handling
- https://mastra.ai/docs/workflows/dynamic-workflows
- https://mastra.ai/reference/workflows/workflow
- https://mastra.ai/reference/workflows/step
- https://mastra.ai/reference/workflows/run
- https://mastra.ai/reference/streaming/workflows/stream
