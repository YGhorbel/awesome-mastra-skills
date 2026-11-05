# Schedules API reference

Distilled from `https://mastra.ai/reference/schedules/overview.md`, `https://mastra.ai/docs/harness/schedules.md`, and `https://mastra.ai/docs/workflows/scheduled-workflows.md`. Added in `@mastra/core@1.50.0`.

## Contents

- Methods
- Agent schedule input
- Workflow schedule input
- Patch rules
- Hooks
- Declarative workflow schedule
- IDs
- Delivery guarantees
- Topology and storage
- Client and HTTP

---

## Methods

| Method | Notes |
|---|---|
| `mastra.schedules.create(input)` | `agentId` for agent schedules, `workflowId` for workflow schedules. Starts the scheduler on first create. |
| `get(id)` | Bare agent IDs resolve to `agent_<slug>` |
| `list(filter?)` | `agentId`, `workflowId`, `threadId`, `resourceId`, `name`, `status`. Default omits `completed`. |
| `update(id, patch)` | Changing `cron` or `timezone` recomputes `nextFireAt` |
| `pause(id)` | Durable, idempotent |
| `resume(id)` | Recomputes `nextFireAt` from now. No future occurrence completes it. |
| `run(id)` | Fire once now. Cadence unchanged. Agent `claimId` `manual_<id>_<ts>`, workflow `sched_<id>_<ts>` (reused as run ID). |
| `delete(id)` | Missing ID is a no-op |

---

## Agent schedule input

| Field | Notes |
|---|---|
| `id` | Optional, normalized to `agent_<slug>` |
| `agentId` | Required |
| `cron` | Required. 5, 6, or 7 parts, or Croner nicknames (`@hourly`, `@daily`, `@weekly`, `@monthly`, `@midnight`) |
| `prompt` | Required |
| `name` | Label for several schedules on one agent or thread |
| `timezone` | IANA. Default host local time. |
| `threadId` | Omit for threadless `agent.generate()` fires |
| `resourceId` | Required with `threadId` |
| `signalType` | Default `notification`. Needs `threadId`. |
| `tagName` | Default `schedule` |
| `attributes` | XML tag attributes |
| `providerOptions` | JSON-safe, merged into every fire |
| `ifActive` | `{ behavior: 'deliver' \| 'persist' \| 'discard' }`. Needs `threadId`. |
| `ifIdle` | `{ behavior: 'wake' \| 'persist' \| 'discard', streamOptions? }`. Needs `threadId`. |
| `metadata` | Stored with the row |
| `status` | `'active'` (default) or `'paused'` |

---

## Workflow schedule input

| Field | Notes |
|---|---|
| `id` | Optional, normalized to `schedule_<slug>` |
| `workflowId` | Required |
| `cron` | Required |
| `timezone` | IANA |
| `inputData` | Workflow input |
| `initialState` | Workflow state |
| `requestContext` | `Record<string, unknown>` |
| `metadata` | |
| `status` | `'active'` or `'paused'` |

---

## Patch rules

- Agent patches: `cron`, `timezone`, `prompt`, `name`, `signalType`, `tagName`, `attributes`, `providerOptions`, `ifActive`, `ifIdle`, `metadata`, `status`.
- `threadId` and `resourceId` are not patchable.
- Workflow patches: `cron`, `timezone`, `inputData`, `initialState`, `requestContext`, `metadata`, `status`. Agent-only fields throw.
- `status` from `paused` to `active` recomputes the next fire.
- A cadence edit with no future occurrence completes the row, even if paused. A cadence edit that can fire reactivates a completed row.

---

## Hooks

Configure once on `new Mastra({ schedules: { ... } })`. Each context includes `agentId`, `schedule`, and `trigger`.

| Hook | Runs | Return |
|---|---|---|
| `prepare({ agentId, schedule, trigger })` | Before each fire | Overrides object (for example `{ prompt }` or `{ threadId }`), `null` to skip, `undefined` for defaults |
| `onFinish({ agentId, outcome, runId })` | Non-error, non-abort outcome. Threaded: when the run starts. | |
| `onError({ agentId, phase, error })` | `prepare` or signal failure, or a threadless run error | |
| `onAbort({ agentId, runId })` | Threadless run aborted | |

Hook exceptions are caught and logged. `trigger.firedAt` is a `Date`.

---

## Declarative workflow schedule

`createWorkflow({ id, ..., schedule })` where `schedule` is an object or an array of objects.

| Field | Notes |
|---|---|
| `id` | Required per entry in an array, stable |
| `cron` | Required, validated at construction |
| `timezone` | IANA |
| `inputData` | Input on every fire |
| `initialState` | |
| `requestContext` | |
| `metadata` | |

Redeploy diff: `cron` or `timezone` change recomputes `nextFireAt`. Data-only change patches in place. User-set status and history are kept. Removed array entries are deleted on boot.

Evented engine: with `MASTRA_WORKERS` set, scheduled workflows build on the evented engine (needs `@mastra/libsql` or `@mastra/pg`). If you split workers with the `workers` option instead, import `createWorkflow` from `@mastra/core/workflows/evented`.

---

## IDs

| Origin | Format |
|---|---|
| Agent schedule via service | `agent_<slug>` or `agent_<uuid>` |
| Workflow schedule via service | `schedule_<slug>` or `schedule_<uuid>` |
| Declarative single | `wf_<workflowId>` |
| Declarative array entry | `wf_<workflowId>__<scheduleId>` |

---

## Delivery guarantees

- Claim and advance `nextFireAt` atomically, then publish with up to three attempts (100 ms, then 200 ms waits).
- After failures: log with `publicationOutcome: 'unknown'`, call `scheduler.onError`, record a `failed` trigger if possible.
- No replay of skipped occurrences. Duplicates possible on retry or transport redelivery.
- Before manual reruns, check target execution records independently.

---

## Topology and storage

| Host | Scheduler |
|---|---|
| `mastra build` server on a long-lived host | Starts automatically |
| Server adapter | Call `mastra.startWorkers()` after listening |
| Split workers | `MASTRA_WORKERS=scheduler` on exactly one process |
| Serverless | Built-in scheduler does not fire. Use `@mastra/inngest`. |

Storage with the schedules domain: `@mastra/libsql`, `@mastra/pg`, `@mastra/mysql`, `@mastra/mongodb`, `@mastra/convex`, `@mastra/spanner`.

---

## Client and HTTP

- `@mastra/client-js`: `client.pauseSchedule(id)`, `client.resumeSchedule(id)`, plus agent schedule methods over `/api/schedules` (see the client-js agents reference).
- Routes: `POST /api/schedules/:scheduleId/pause` and `/resume`, requiring `schedules:write`.
- Studio: `/workflows/schedules`, `?workflowId=<id>`, and `/workflows/schedules/:scheduleId` with trigger history and Pause/Resume.
- Inngest schedules do not appear in Studio and are not controlled by these calls.
