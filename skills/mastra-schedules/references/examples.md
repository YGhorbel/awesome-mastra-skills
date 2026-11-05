# Schedule examples

All examples follow the current docs. Schedules need `@mastra/core@1.50.0` or later and storage with the schedules domain.

## Contents

1. Daily threaded summary into a conversation
2. Per-user schedules with a prepare hook
3. Workflow with several cadences
4. Pause and resume from a client
5. Scheduler with a server adapter

---

## 1. Daily threaded summary into a conversation

```typescript
import { Mastra } from '@mastra/core'
import { Agent } from '@mastra/core/agent'
import { LibSQLStore } from '@mastra/libsql'
import { Memory } from '@mastra/memory'

const storage = new LibSQLStore({ id: 'mastra-storage', url: 'file:./mastra.db' })

const assistant = new Agent({
  id: 'assistant',
  name: 'Assistant',
  instructions: 'Keep the user up to date. On a <check-in> signal, summarize what changed.',
  model: 'openai/gpt-6.1-sol',
  memory: new Memory({ storage }),
})

export const mastra = new Mastra({ agents: { assistant }, storage })

await mastra.schedules.create({
  id: 'daily-check-in',
  agentId: 'assistant',
  cron: '0 9 * * *',
  timezone: 'Europe/Paris',
  prompt: 'Summarize anything new since yesterday.',
  threadId: 'thread-123',
  resourceId: 'user-456',
  tagName: 'check-in', // renders as <check-in>...</check-in>
  attributes: { source: 'cron' },
  ifActive: { behavior: 'discard' }, // skip if the thread is mid-stream
  ifIdle: {
    behavior: 'wake',
    streamOptions: { requestContext: { locale: 'en-US' } },
  },
})
```

---

## 2. Per-user schedules with a prepare hook

```typescript
import { Mastra } from '@mastra/core'
import { LibSQLStore } from '@mastra/libsql'
import { pinger } from './agents/pinger' // the pinger agent from SKILL.md

export const mastra = new Mastra({
  agents: { pinger },
  storage: new LibSQLStore({ id: 'mastra-storage', url: 'file:./mastra.db' }),
  schedules: {
    prepare: async ({ agentId, schedule, trigger }) => {
      if (agentId !== 'pinger') return undefined
      return { prompt: `Status as of ${trigger.firedAt.toISOString()}` }
    },
    onFinish: async ({ agentId, outcome, runId }) => {
      console.log('schedule finished', agentId, outcome, runId)
    },
    onError: async ({ agentId, phase, error }) => {
      console.error('schedule failed', agentId, phase, error)
    },
  },
})

// Create one schedule per user, then manage it by id
export async function enableWeeklyDigest(userId: string) {
  return mastra.schedules.create({
    id: `weekly-digest-${userId}`,
    agentId: 'pinger',
    name: 'weekly-digest',
    cron: '0 8 * * 1',
    timezone: 'America/New_York',
    prompt: 'Write my weekly digest.',
    metadata: { userId },
  })
}

const active = await mastra.schedules.list({ agentId: 'pinger', status: 'active' })
await mastra.schedules.update('weekly-digest-u1', { cron: '0 7 * * 1' })
await mastra.schedules.run('weekly-digest-u1') // fire once now
await mastra.schedules.delete('weekly-digest-u1')
```

Return `null` from `prepare` to skip a fire.

---

## 3. Workflow with several cadences

```typescript
import { createWorkflow, createStep } from '@mastra/core/workflows'
import { z } from 'zod'

const check = createStep({
  id: 'check',
  inputSchema: z.object({ window: z.string() }),
  outputSchema: z.object({ ok: z.boolean() }),
  execute: async ({ inputData }) => {
    // run the check for inputData.window
    return { ok: true }
  },
})

export const statusCheck = createWorkflow({
  id: 'status-check',
  inputSchema: z.object({ window: z.string() }),
  outputSchema: z.object({ ok: z.boolean() }),
  schedule: [
    { id: 'morning', cron: '0 9 * * *', timezone: 'UTC', inputData: { window: 'morning' } },
    { id: 'evening', cron: '0 18 * * *', timezone: 'UTC', inputData: { window: 'evening' } },
  ],
})
  .then(check)
  .commit()
```

Rows `wf_status-check__morning` and `wf_status-check__evening` appear in Studio at `/workflows/schedules?workflowId=status-check`.

Runtime alternative without code changes:

```typescript
await mastra.schedules.create({
  workflowId: 'status-check',
  cron: '0 12 * * *',
  timezone: 'UTC',
  inputData: { window: 'noon' },
})
```

---

## 4. Pause and resume from a client

```typescript
import { MastraClient } from '@mastra/client-js'

const client = new MastraClient({ baseUrl: 'http://localhost:4111' })

await client.pauseSchedule('wf_status-check__evening')
// investigate, ship a fix, then:
await client.resumeSchedule('wf_status-check__evening')
```

Both routes need the `schedules:write` permission. Resume fires on the next regular tick, with no backlog.

---

## 5. Scheduler with a server adapter

The `mastra build` server starts the scheduler itself. A server adapter does not:

```typescript
// after your HTTP server starts listening
await mastra.startWorkers()
```

For split deployments, run one process with `MASTRA_WORKERS=scheduler` and use a storage adapter with the schedules domain.
