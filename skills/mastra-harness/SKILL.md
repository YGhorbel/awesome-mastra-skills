---
name: mastra-harness
description: "Run Mastra agents beyond a single request with the harness capabilities: durable agents that survive disconnects and restarts (createDurableAgent, createEventedAgent, createInngestAgent, durable: true), background tasks for slow tools and subagents, thread-scoped goals judged until done, AgentController sessions with modes, approvals, subagents, and channels, workers, and the coding agent factory (createCodingAgent, buildBasePrompt) plus the Mastra Code SDK (mountAgentControllerOnMastra, ACP server). Use this skill whenever the user wants a long-running, resumable, steerable, or interactive agent, a coding agent, a plan-then-build mode switch, or work that keeps going after the HTTP request ends. Triggers on harness, DurableAgent, observe(runId), resumable stream, crash recovery, backgroundTasks, untilIdle, setObjective, goal judge, AgentController, createSession, session.steer, respondToToolApproval, submit_plan, MASTRA_WORKERS, @mastra/code-sdk, mastracode --acp."
license: Apache-2.0
metadata:
  category: harness
  catalog_summary: "Durable agents, background tasks, goals, AgentController sessions, workers, and the coding agent factory"
  display_order: 1
  docs: https://mastra.ai/docs/harness/overview
---

# Mastra Harness

Pick and wire the harness capabilities that keep an agent's work durable, visible, and steerable across retries, disconnects, restarts, and long-running goals.

---

## When to use

- A client may disconnect mid-stream and must reconnect without losing chunks
- A run must survive a process crash or rolling deploy
- A tool, workflow, or subagent is slow and should not block the agent's reply
- An agent should keep working toward one objective until a judge says it is done
- Building an interactive product: sessions per user, plan and build modes, tool approvals, steering, follow-ups
- Building a coding agent with a workspace, task tracking, and retry defaults
- Serving Mastra Code to your own UI or an ACP editor client
- Splitting API, scheduler, and background-task workers into separate processes

## When NOT to use

- A plain request-response agent (use `mastra-agents`)
- Cron-driven runs of agents or workflows (use `mastra-schedules`)
- Sending messages, state, or notifications into a thread, signal providers, and cross-process leases (use `mastra-signals`)
- Tool approval on a regular agent outside AgentController (use `mastra-agent-approval-hitl`)
- Supervisor agents and `isTaskComplete` (use `mastra-multi-agent`)
- Workspace filesystems and sandboxes in depth (use `mastra-workspace-sandbox`)
- Chat platform adapters such as Slack (use `mastra-channels`)
- Container topology and deploy targets for workers (use `mastra-deployment`)

---

## Required inputs

- What must survive: a client disconnect, a process crash, or only a slow tool
- Storage adapter (required for background tasks, goals, recovery, and controller threads)
- PubSub and cache backends if more than one process serves the agent (Redis Streams, Redis cache)
- For goals: the objective, the judge model, and the run budget (`maxRuns`)
- For AgentController: modes, which tools need approval, subagent types, the UI type (in-process or browser)
- For coding agents: the repository path and whether commands may run on the host

---

## The framework: pick the capability

| Need | Capability | Entry point |
|---|---|---|
| Reconnectable, crash-recoverable runs | Durable agent | `createDurableAgent({ agent })` from `@mastra/core/agent/durable`, or `durable: true` |
| Fire-and-forget runs | Evented agent | `createEventedAgent({ agent })` |
| Production step memoization and retries | Inngest agent | `createInngestAgent({ agent, inngest })` from `@mastra/inngest` |
| Slow tools without blocking | Background tasks | `new Mastra({ backgroundTasks: { enabled: true } })` plus tool or agent opt-in |
| Keep going until done | Goals | Agent `goal: { judge, maxRuns }` and `agent.setObjective()` |
| Interactive sessions, modes, approvals | AgentController | `new AgentController({...})` from `@mastra/core/agent-controller` |
| Coding agent defaults | Coding agent | `createCodingAgent()` from `@mastra/core/coding-agent` |
| Mastra Code in your app | Code SDK | `mountAgentControllerOnMastra()` from `@mastra/code-sdk` |

Capabilities compose. A coding agent can be the backing agent of an AgentController, have a goal, and dispatch background tasks.

### Durable agent in one screen

```typescript
import { Mastra } from '@mastra/core'
import { Agent } from '@mastra/core/agent'
import { createDurableAgent } from '@mastra/core/agent/durable'

const agent = new Agent({
  id: 'researcher',
  name: 'Researcher',
  instructions: 'You research topics thoroughly.',
  model: 'openai/gpt-6.1-sol',
})

export const durableResearcher = createDurableAgent({ agent })
export const mastra = new Mastra({ agents: { durableResearcher } })

const { output, runId, cleanup } = await durableResearcher.stream('Research quantum computing advances')
for await (const chunk of output.fullStream) {
  // render
}
cleanup()

// From another request after a disconnect:
const { output: resumed } = await durableResearcher.observe(runId)
```

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/` and the installed types for `DurableAgent`, `AgentController`, and `Session`. Otherwise fetch `https://mastra.ai/docs/harness/overview.md` and the page for each capability you use. Durable agents and workers are beta. Trust these over memory.
2. **Choose the smallest capability set** from the table. Do not add AgentController when a durable agent alone solves the problem.
3. **Configure storage** on `Mastra`. Background tasks, goals, crash recovery, and controller threads need it.
4. **Durable agents:** wrap with `createDurableAgent` or set `durable: true` on the agent (applied at registration). Keep the `runId`. Call `cleanup()` when done, except for suspended runs you will resume.
5. **Multi-process:** share a cache (`RedisServerCache` from `@mastra/redis`), a PubSub backend, and run storage. Set `recovery: { durableAgents: 'auto' }` for boot-time recovery.
6. **Background tasks:** enable on `Mastra`, then opt in per tool (`background: { enabled: true }`) or per agent (`backgroundTasks.tools`). Use `untilIdle: true` on `stream()` when the caller should see follow-up turns.
7. **Goals:** add `goal: { judge, maxRuns }` to an agent with memory. Call `setObjective(text, { threadId, resourceId })`, then stream on that thread.
8. **AgentController:** define modes, call `controller.init()` once, create one Session per user or task, subscribe before `sendMessage()`, and handle `tool_approval_required` and `tool_suspended` events.
9. **Coding agents:** build with `createCodingAgent({ id, name, model, instructions })`. Swap the default local workspace for a sandbox when untrusted code runs.
10. **Make tools idempotent.** Recovery and retries can re-execute tool calls and whole subagent delegations.

---

## Deep dive: AgentController sessions

```typescript
import { Agent } from '@mastra/core/agent'
import { AgentController } from '@mastra/core/agent-controller'
import { LocalFilesystem, Workspace } from '@mastra/core/workspace'
import { LibSQLStore } from '@mastra/libsql'

const controller = new AgentController({
  id: 'assistant-controller',
  agent: new Agent({
    id: 'assistant',
    name: 'Assistant',
    instructions: 'Help the user plan and complete tasks.',
    model: 'openai/gpt-6.1-sol',
  }),
  storage: new LibSQLStore({ id: 'agent-controller-storage', url: 'file:./mastra.db' }),
  workspace: new Workspace({
    id: 'assistant-workspace',
    filesystem: new LocalFilesystem({ basePath: './workspace' }),
  }),
  modes: [
    { id: 'plan', name: 'Plan', metadata: { default: true }, instructions: 'Reason before changing anything.', transitionsTo: 'build' },
    { id: 'build', name: 'Build', instructions: 'Implement the approved plan.' },
  ],
})

await controller.init()
const session = await controller.createSession({ id: 'user-123:web', resourceId: 'user-123' })

session.subscribe(event => {
  if (event.type === 'message_update' && event.event.type === 'text-delta') process.stdout.write(event.event.delta)
  if (event.type === 'tool_approval_required') session.respondToToolApproval({ toolCallId: event.toolCallId, decision: 'approve' })
})

await session.sendMessage({ content: 'Plan a small TypeScript CLI.' })
await session.steer({ content: 'Focus on argument parsing first.' }) // aborts and redirects
await session.followUp({ content: 'Then add tests.' }) // queued until idle
```

Lifetimes: the controller is shared and initialized once. A Session is live, process-local state (mode, model, grants, pending approvals). Threads and thread settings persist in storage. Register the controller on `new Mastra({ agentControllers: { controller } })` to expose it over HTTP and channels.

---

## Failure patterns

- **Durable stream replay is empty.** `cleanup()` ran, or `cleanupTimeoutMs` (30 s default) passed. Raise `cleanupTimeoutMs` or use a persistent cache.
- **`observe()` throws `DURABLE_AGENT_OBSERVE_AGENT_MISMATCH`.** The observing DurableAgent must have the same effective `id` as the one that started the run.
- **Reconnect works locally but not across replicas.** The default cache and `EventEmitterPubSub` are in-process. Share a Redis cache, PubSub, and storage.
- **Nothing recovered after a crash.** With `recovery.durableAgents: 'off'` (default), `running` checkpoints are not written. Set `'auto'` or a `shouldPersistSnapshot` that includes `running`.
- **Duplicate side effects after recovery.** Recovery replays from the last snapshot. Make tools idempotent and honor `abortSignal`.
- **`cleanup()` called on a suspended durable run.** It destroys the registry entry. Let auto-cleanup handle it and call `resume()` later.
- **Background tasks never run in the background.** `backgroundTasks.enabled` is false, storage is missing, or the tool was not opted in. `_background` from the model cannot enable an ineligible tool.
- **Goal does nothing.** No `judge` resolved, or the thread has no memory and storage. The judge is the activation switch.
- **Goal stops early with status `paused`.** `maxRuns` was hit. Raise it with `updateObjectiveOptions()`.
- **Session state lost on restart.** `session.state`, grants, and pending approvals are live only. Persist what you need yourself.
- **Several users share one Session.** Create one Session per user or task. Do not route messages through the controller.
- **Coding agent runs commands on the host.** The default workspace uses `LocalSandbox`. Pass a remote sandbox workspace for untrusted work.
- **`createCodingAgent` without memory has no task tools.** `TaskSignalProvider` is added only when `memory` is set.

---

## Output format

A finished harness delivery contains:

- The agent definition and its wrapper (`createDurableAgent`, `createCodingAgent`, or an `AgentController`)
- `new Mastra({...})` with storage, plus `backgroundTasks`, `recovery`, `pubsub`, or `agentControllers` as used
- Client or route code that keeps `runId` and calls `observe()`, or subscribes to Session events
- Idempotency notes or guards on side-effecting tools
- Env vars in `.env.example` (`REDIS_URL`, `DATABASE_URL`, `MASTRA_WORKERS` for split deployments)
- A test that disconnects and reconnects, or kills and recovers a run

---

## Reference files

- [`references/api.md`](references/api.md) - DurableAgent factories, options, and methods; background task config; goal config and methods; AgentController and Session API; coding agent and Code SDK; workers.
- [`references/examples.md`](references/examples.md) - Reconnectable durable agent with Redis, background research tool, goal-driven worker, coding agent with tasks and goal.
- [`references/checklist.md`](references/checklist.md) - Production checklist for long-running agents.

**Live docs**

- https://mastra.ai/docs/harness/overview
- https://mastra.ai/docs/harness/durable-agents
- https://mastra.ai/docs/harness/background-tasks
- https://mastra.ai/docs/harness/goals
- https://mastra.ai/docs/harness/agent-controller
- https://mastra.ai/reference/agents/durable-agent
- https://mastra.ai/reference/agent-controller/agent-controller-class
- https://mastra.ai/reference/agent-controller/session
- https://mastra.ai/reference/coding-agent/create-coding-agent
- https://mastra.ai/reference/coding-agent/build-base-prompt
- https://mastra.ai/reference/code-sdk/mount-agent-controller
- https://mastra.ai/reference/code-sdk/acp-server
- https://mastra.ai/reference/workers/overview
