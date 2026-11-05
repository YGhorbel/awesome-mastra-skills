---
name: mastra-schedules
description: "Run Mastra agents and workflows on a cron cadence: create, list, update, pause, resume, run, and delete persisted schedules through mastra.schedules, declare a schedule field on createWorkflow, send threaded schedule fires as signals into a conversation, and hook prepare, onFinish, onError, and onAbort. Use this skill whenever the user wants a daily summary, an hourly check, a weekly report, a recurring nudge into a chat thread, a cron job for an agent or workflow, or needs to pause a misfiring schedule in production. Triggers on mastra.schedules, schedules.create, cron, timezone, scheduled workflow, schedule field on createWorkflow, pauseSchedule, resumeSchedule, wf_ schedule id, agent_ schedule id, threadless versus threaded schedule, SchedulerWorker, MASTRA_WORKERS scheduler, Studio schedules view. Also triggers when schedules do not fire on serverless hosts or with a server adapter."
license: Apache-2.0
metadata:
  category: harness
  catalog_summary: "Persisted cron schedules for agents and workflows, threaded fires, hooks, pause and resume, and scheduler topology"
  display_order: 2
  docs: https://mastra.ai/docs/harness/schedules
---

# Mastra Schedules

Fire agents and workflows on a cron cadence with persisted, pausable schedules, and deploy the scheduler where it can actually tick.

---

## When to use

- An agent should run on a cadence (status checks, daily summaries, periodic triage)
- A recurring prompt should land in an existing conversation thread
- A workflow should start on a cron with fixed input
- Schedules must be created, edited, paused, or deleted at runtime (from code, a UI, or the client SDK)
- Computing fire-time parameters, or skipping a fire, with a `prepare` hook
- Debugging schedules that never fire or fire at the wrong time

## When NOT to use

- One-off delayed work or slow tools inside a run (use `mastra-harness` background tasks)
- Sending signals or notifications into a thread outside a cron (use `mastra-signals`)
- Defining workflow steps, branching, and suspend/resume (use `mastra-workflows` and `mastra-workflow-suspend-resume`)
- Schedules for agents defined as files (use `mastra-file-based-agents`)
- Worker containers and hosting targets (use `mastra-deployment`)
- Inngest-native cron functions (use `mastra-workflows` with the Inngest integration)

---

## Required inputs

- Target: an agent ID with a prompt, or a workflow ID with input data
- Cadence as cron (5, 6, or 7 parts, or `@daily` style nicknames) and an IANA timezone
- Threadless (isolated `generate()` run) or threaded (`threadId` plus `resourceId`)
- A storage adapter with the schedules domain: `@mastra/libsql`, `@mastra/pg`, `@mastra/mysql`, `@mastra/mongodb`, `@mastra/convex`, or `@mastra/spanner`
- The host: long-lived server, server adapter, split workers, or serverless

---

## The framework: one service, two declaration styles

| | Runtime schedules | Declarative workflow schedules |
|---|---|---|
| Created by | `mastra.schedules.create({...})` | `schedule` field on `createWorkflow` |
| Targets | Agents (`agentId`) or workflows (`workflowId`) | That workflow |
| ID | `agent_<slug or uuid>` or `schedule_<slug or uuid>` | `wf_<workflowId>` or `wf_<workflowId>__<id>` |
| Edit | `update()`, `pause()`, `resume()`, `delete()` | Change code and redeploy. Pause and resume still work. |
| Storage | Persisted rows | Persisted rows, upserted on boot |

```typescript
import { Mastra } from '@mastra/core'
import { Agent } from '@mastra/core/agent'
import { LibSQLStore } from '@mastra/libsql'

const pinger = new Agent({
  id: 'pinger',
  name: 'Pinger',
  instructions: 'Report the current system status in one sentence.',
  model: 'openai/gpt-6.1-sol',
})

const mastra = new Mastra({
  agents: { pinger },
  storage: new LibSQLStore({ id: 'mastra-storage', url: 'file:./mastra.db' }),
})

// Threadless: each fire is an isolated agent.generate() run
await mastra.schedules.create({
  id: 'hourly-status',
  agentId: 'pinger',
  cron: '0 * * * *',
  timezone: 'America/New_York',
  prompt: 'Give me a status update.',
})

// Threaded: each fire is a signal into the conversation
await mastra.schedules.create({
  agentId: 'pinger',
  cron: '0 9 * * 1-5',
  prompt: 'Summarize anything new since yesterday.',
  threadId: 'thread-123',
  resourceId: 'user-456',
  ifActive: { behavior: 'discard' },
  ifIdle: { behavior: 'wake' },
})
```

### Delivery is best-effort

The scheduler claims an occurrence, advances `nextFireAt`, then publishes with up to three attempts. A crash or exhausted attempts can skip an occurrence, and skipped occurrences are never replayed. Retries can publish duplicates. Design targets to tolerate both. `completed` means the cron has no future occurrence, not that the run succeeded.

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/` and the installed `mastra.schedules` types. Otherwise fetch `https://mastra.ai/docs/harness/schedules.md`, `https://mastra.ai/reference/schedules/overview.md`, and `https://mastra.ai/docs/workflows/scheduled-workflows.md`. Schedules need `@mastra/core@1.50.0` or later. Trust these over memory.
2. **Configure storage** with the schedules domain on `new Mastra({ storage })`.
3. **Pick the style.** Fixed workflow cadence in code: `schedule` on `createWorkflow`. Anything created per user or at runtime: `mastra.schedules.create()`.
4. **Write the cron and timezone.** Always set `timezone` in production. Validate the cron by creating the schedule (invalid crons throw).
5. **Choose threadless or threaded** for agents. Threaded fires need `resourceId` and accept signal fields (`signalType`, `tagName`, `attributes`, `ifActive`, `ifIdle`).
6. **Give a stable `id`** when code must look the schedule up later. IDs normalize to `agent_<slug>` or `schedule_<slug>`.
7. **Add hooks** under `new Mastra({ schedules: { prepare, onFinish, onError, onAbort } })` when fire-time values or outcome handling are needed. Branch on `agentId`.
8. **Make the scheduler tick.** The `mastra build` server starts it. With a server adapter, call `mastra.startWorkers()` after listening. On serverless, use Inngest cron instead.
9. **Operate.** Use `pause`, `resume`, and `run` from code, `client.pauseSchedule()` from a client, or Studio at `/workflows/schedules`.
10. **Verify** with `mastra.schedules.run(id)` and inspect trigger history in Studio.

---

## Deep dive: declarative workflow schedules

```typescript
import { createWorkflow, createStep } from '@mastra/core/workflows'
import { z } from 'zod'

const sendReport = createStep({
  id: 'send-report',
  inputSchema: z.object({ userId: z.string() }),
  outputSchema: z.object({ ok: z.boolean() }),
  execute: async ({ inputData }) => ({ ok: true }),
})

export const dailyReport = createWorkflow({
  id: 'daily-report',
  inputSchema: z.object({ userId: z.string() }),
  outputSchema: z.object({ ok: z.boolean() }),
  schedule: {
    cron: '0 9 * * *',
    timezone: 'America/New_York',
    inputData: { userId: 'system' },
  },
})
  .then(sendReport)
  .commit()
```

Pass an array of entries with unique `id` values for several cadences. On redeploy, a changed `cron` or `timezone` recomputes `nextFireAt`, changed `inputData` patches in place, a user-set pause is preserved, and removed entries are deleted.

Split deployments: when `MASTRA_WORKERS` is set (even to `false`), `createWorkflow` builds scheduled workflows on the evented engine, which needs `@mastra/libsql` or `@mastra/pg`. Run exactly one scheduler worker.

---

## Failure patterns

- **Schedules never fire with a server adapter.** Adapters do not start workers. Call `mastra.startWorkers()` after the server listens.
- **Schedules never fire on Vercel, Netlify, Lambda, or Workers.** The tick loop needs a long-lived process. Use `@mastra/inngest` cron or a long-lived host.
- **Storage has no schedules domain.** Upstash, DynamoDB, D1, ClickHouse, and Redis lack it. Use libSQL, Postgres, MySQL, MongoDB, Convex, or Spanner.
- **Fires at the wrong hour.** No `timezone`, so the host locale applies. Set an IANA timezone.
- **Duplicate fires.** More than one scheduler worker, or publish retries. Run one scheduler and make targets idempotent.
- **`threadId` without `resourceId`.** Threaded schedules require both. `signalType`, `ifActive`, and `ifIdle` require `threadId`.
- **Trying to move a threaded schedule.** `threadId` and `resourceId` are not patchable. Create a new schedule and delete the old one.
- **Agent-only patch on a workflow schedule** (`prompt`, `ifIdle`) throws.
- **Editing code does not unpause.** A paused declarative schedule stays paused until `resumeSchedule` or Studio Resume.
- **Expecting `onFinish` at run end for threaded schedules.** It fires when the signal starts the run. Errors after that surface on the thread's run.
- **Backlog expected after resume.** Resume recomputes from now. Missed occurrences are not replayed.
- **Confusing Mastra Code `/schedules`** with `mastra.schedules`. The former is process-local and not persisted.

---

## Output format

A finished schedule delivery contains:

- Storage with the schedules domain on the `Mastra` instance
- Either a `schedule` field on the workflow or a `mastra.schedules.create()` call with a stable `id`
- Explicit `timezone` on every schedule
- Hooks in `new Mastra({ schedules })` if fire-time values or outcome handling are required
- A note on how the scheduler runs (built server, `startWorkers()`, scheduler worker, or Inngest)
- Evidence: a manual `run()` and the trigger row in Studio

---

## Reference files

- [`references/api.md`](references/api.md) - `mastra.schedules` methods, agent and workflow input fields, patch rules, hooks, declarative fields, IDs, topology.
- [`references/examples.md`](references/examples.md) - Daily threaded summary, per-user schedules with hooks, multi-cadence workflow, client pause and resume.
- [`references/checklist.md`](references/checklist.md) - Schedule production checklist.

**Live docs**

- https://mastra.ai/docs/harness/schedules
- https://mastra.ai/docs/workflows/scheduled-workflows
- https://mastra.ai/reference/schedules/overview
- https://mastra.ai/reference/workers/overview
- https://mastra.ai/docs/deployment/workers
