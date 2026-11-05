# Harness checklist

Run this before calling a long-running agent done.

## Choice

- [ ] The smallest capability set is used (durable agent, background tasks, goals, controller)
- [ ] Beta status of durable agents and workers is acknowledged

## Durability

- [ ] Storage configured on `Mastra`
- [ ] `runId` returned to clients and used with `observe()` for reconnects
- [ ] `cleanup()` called when done, never on runs you will resume
- [ ] `cleanupTimeoutMs` covers the replay window you need
- [ ] Shared cache, PubSub, and storage when more than one process serves runs
- [ ] `recovery.durableAgents: 'auto'` or a `shouldPersistSnapshot` that includes `running` when crash recovery matters
- [ ] Workflows store supports run fencing, or recovery runs behind leader election
- [ ] Hooks that must survive restart live in `defaultOptions.delegation`, not per call

## Side effects

- [ ] Every side-effecting tool is idempotent or deduplicated
- [ ] Tools honor `abortSignal`
- [ ] Subagent tools are idempotent too (recovery replays whole delegations)

## Background tasks and goals

- [ ] `backgroundTasks.enabled` set and each slow tool opted in
- [ ] Timeouts and concurrency limits set
- [ ] Callers needing follow-up turns use `untilIdle`
- [ ] No double notification (`notifyAgentOnFinish: false` if you send your own)
- [ ] Goal has a `judge`, a sensible `maxRuns`, and verification `tools` if output alone is not enough

## AgentController

- [ ] `controller.init()` called once, one Session per user or task
- [ ] Subscribe before sending messages
- [ ] `tool_approval_required` and `tool_suspended` handled in the UI
- [ ] Session state, grants, and approvals restored by the host if needed after restarts
- [ ] Registered on `new Mastra({ agentControllers })` when exposed over HTTP or channels

## Coding agents and workers

- [ ] Commands run in a sandbox when code is untrusted
- [ ] `memory` set when task tracking is wanted
- [ ] Exactly one scheduler worker in split deployments
- [ ] `MASTRA_STEP_EXECUTION_URL` uses HTTPS and `MASTRA_WORKER_AUTH_TOKEN` is set when workers run separately
