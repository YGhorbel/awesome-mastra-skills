# Harness API reference

Distilled from the harness docs and `reference/agents/durable-agent`, `reference/agent-controller/*`, `reference/coding-agent/*`, `reference/code-sdk/*`, and `reference/workers/overview`. Verify against the installed version.

## Contents

- Durable agent factories
- DurableAgent methods
- Durable stream options (selected)
- Recovery and run ownership
- Background tasks
- Goals
- AgentController constructor
- AgentController methods
- Session API
- Coding agent
- Code SDK
- Workers

---

## Durable agent factories

Import from `@mastra/core/agent/durable` (Inngest from `@mastra/inngest`).

| Factory | Use | Notes |
|---|---|---|
| `createDurableAgent({ agent, ... })` | Local and single process | Stream awaited in-process |
| `createEventedAgent({ agent, ... })` | Background execution | Always persists full snapshot set |
| `createInngestAgent({ agent, inngest })` | Production on Inngest | No cache by default. Persists only `suspended`. |
| Agent `durable: true \| { maxSteps, cleanupTimeoutMs, cache, pubsub, shouldCache, shouldPersistSnapshot }` | Wrap at registration | Unregistered agents are not wrapped |

Options:

| Option | Default | Notes |
|---|---|---|
| `agent` | required | |
| `id`, `name` | from agent | Effective id must match for `observe()` |
| `cache` | Mastra cache or in-memory | `false` disables replay |
| `pubsub` | `EventEmitterPubSub` | |
| `maxSteps` | | |
| `shouldCache(topic)` | | Return false to skip replay cache for a topic |
| `shouldPersistSnapshot({ stepResults, workflowStatus })` | see Recovery | Ignored by evented and Inngest agents |
| `cleanupTimeoutMs` | `30000` | `0` disables auto-cleanup |

Stored agents created through the client accept `durable: true` or `{ maxSteps, cleanupTimeoutMs }`.

---

## DurableAgent methods

| Method | Returns / notes |
|---|---|
| `stream(messages, options?)` | `{ output, fullStream, runId, threadId?, resourceId?, cleanup, abort }` |
| `resume(runId, resumeData, options?)` | New stream. Waits 5 s for a live claim, then `DURABLE_AGENT_EXECUTION_CONFLICT`. |
| `observe(runId, { offset?, idleTimeoutMs?, isAlive?, onChunk? })` | Replays cached events, then live. Also returns `detach()`. |
| `prepare(messages, options?)` | `{ runId, messageId, workflowInput, registryEntry, threadId?, resourceId? }` |
| `abortRunStream(runId)` | `boolean`. Needs shared PubSub across processes. Not on Inngest. |
| `abortThreadStream({ threadId, resourceId?, expectedRunId? })` | `boolean` |
| `listActiveRuns({ threadId?, resourceId?, fromDate?, toDate?, perPage?, page? })` | Runs with `running` checkpoints |
| `recoverActiveRuns({ runId? })` | Per-run `success`, `failed`, `skipped` |
| `recover(runId, { force? })` | `force` takes over a live run. Without it throws `DURABLE_AGENT_RUN_ACTIVE`. |

Mastra level: `mastra.recoverAllDurableAgents()` returns `{ recovered, succeeded, failed, skipped }`.

`observe()` without `offset` is the supported reconnect flow. `offset` is a PubSub event index, not a chunk count.

---

## Durable stream options (selected)

`runId`, `instructions`, `context`, `memory`, `requestContext`, `maxSteps`, `toolsets`, `clientTools`, `toolChoice`, `activeTools`, `modelSettings`, `stopWhen`, `system`, `requireToolApproval`, `autoResumeSuspendedTools`, `closeOnSuspend` (default false), `toolCallConcurrency`, `structuredOutput`, `untilIdle`, `disableBackgroundTasks`, `tracingOptions`, `abortSignal`, `onChunk`, `onStepFinish`, `onFinish`, `onError`, `onSuspended`, `onAbort`, `onIterationComplete`.

Closures (`stopWhen`, function `requireToolApproval`, `prepareStep`, per-call `delegation` hooks, `transform` closure) live in the in-process registry and are lost on cross-process resume. Put delegation hooks in the agent's `defaultOptions.delegation`.

---

## Recovery and run ownership

| Setting | Effect |
|---|---|
| `recovery: { durableAgents: 'auto' }` on Mastra | Writes `running` checkpoints each step and recovers orphaned runs on boot |
| `'off'` (default) | Persists `pending`, `paused`, `suspended` only, plus `running` after `mastra.shutdown()` starts |
| `MASTRA_AGENT_THREAD_LEASE_TTL_MS` | Claim lapse time, default 15000 |
| `MASTRA_AGENT_THREAD_LEASE_RENEW_INTERVAL_MS` | Default a third of TTL |

Run fencing (writes from a lost claim rejected) is supported by `InMemoryStore`, `@mastra/pg`, `@mastra/libsql`, `@mastra/turso`, `@mastra/mysql`, `@mastra/mssql`, `@mastra/oracledb`, `@mastra/spanner`, `@mastra/dsql`, `@mastra/cloudflare-d1`, `@mastra/cloudflare` (DO storage), `@mastra/convex`, `@mastra/mongodb` (replica set), `@mastra/dynamodb`, `@mastra/redis`, `@mastra/upstash`, `@mastra/valkey`. Other stores fall back to a PubSub lease.

Recovery concurrency: five agents, five run waits each, 30 s per wait.

---

## Background tasks

Mastra config `backgroundTasks`:

| Key | Notes |
|---|---|
| `enabled` | Required, default off |
| `globalConcurrency`, `perAgentConcurrency`, `perOwnerConcurrency` | Limits |
| `backpressure` | e.g. `'queue'` |
| `defaultTimeoutMs` | |
| `untilIdleMaxIdleMs` | Default idle for `untilIdle: true` |
| `notifyAgentOnFinish` | Set false if you send your own completion signal |
| `wokenRunsEndAfterTurn` | Temporary option |
| `onTaskComplete`, `onTaskFailed` | Global callbacks |

Tool opt-in: `createTool({ ..., background: { enabled, defaultDisposition, timeoutMs, maxRetries, onComplete?, onFailed? } })`.

Agent opt-in: `backgroundTasks: { tools: { name: { enabled, timeoutMs } \| false } \| 'all', disabled?, waitTimeoutMs?, onTaskComplete?, onTaskFailed? }`.

Model override in tool args: `_background: { disposition: 'foreground' \| 'deferred' \| 'awaited', timeoutMs, ... }`.

Manager (`mastra.backgroundTaskManager`): `stream({ agentId?, runId?, threadId?, resourceId?, taskId?, allResources?, abortSignal })`, `getTask(id)`, `listTasks({ status, agentId })`, `resume(taskId, resumeData, { onNoSlot: 'queue' }?)`, `cancel(taskId)`, `registerTaskContext(taskId, ...)`, `registerStaticExecutor(toolName, { execute })`, `enqueue(task, context?, { pinToWorker }?)`.

Suspend inside a tool: `context.agent.suspend(data)`, read `context.agent.resumeData` and `suspendPayload`. HTTP: `POST /api/background-tasks/:id/resume`, client `resumeBackgroundTask(id, data, { suspendedAt })`.

Agent stream chunks: `background-task-started`, `background-task-progress`. Manager chunks: `running`, `output`, `completed`, `failed`, `cancelled`, `suspended`, `resumed` (each prefixed `background-task-`).

---

## Goals

Agent config `goal`:

| Key | Default | Notes |
|---|---|---|
| `judge` | none | Model or resolver. Required to activate. |
| `maxRuns` | `50` | Budget. Exhausted marks objective `paused`. |
| `prompt` | built-in | Judge instructions |
| `tools` | | Read-only verification tools for the judge |
| `maxSteps` | `5` | Judge loop budget |
| `scorer` | default LLM judge | Scorer instance or id. Replaces prompt, tools, maxSteps. |

Methods (need storage and a thread): `setObjective(text, { threadId, resourceId })`, `getObjective({ threadId })`, `updateObjectiveOptions({ threadId, maxRuns, ... })`, `clearObjective({ threadId })`. Each evaluation emits a `goal` chunk. The objective appears to the model as `<current-objective>`.

---

## AgentController constructor

Import: `import { AgentController } from '@mastra/core/agent-controller'`

| Option | Notes |
|---|---|
| `id` | Required. Default session and resource id. |
| `modes` | Required. `{ id, name, instructions?, defaultModelId?, description?, transitionsTo?, availableTools?, tools? \| additionalTools?, metadata: { default } }` |
| `agent` | Shared backing agent |
| `storage`, `memory` | Persistence |
| `workspace`, `browser` | Static or per-session factory |
| `resourceId`, `defaultModeId`, `instructions`, `tools` | |
| `stateSchema`, `initialState` | Session state validation and defaults |
| `subagents` | `{ id, name, description, instructions, tools, allowedControllerTools, allowedWorkspaceTools, defaultModelId, maxSteps, stopWhen, forked }[]` |
| `resolveSubagentModel`, `gateways` | Model resolution |
| `omConfig` | `observerModel`, `reflectorModel` (`'auto'` or id), defaults, `resolveAutoModelId`, thresholds |
| `toolCategoryResolver(toolName)` | Map tools to permission categories |
| `disableBuiltinTools` | e.g. `submit_plan` |
| `channels` | `{ adapters, resolveResourceId, onSessionStart, resolveSession, onStaleToolApproval }` |
| `intervalHandlers`, `idGenerator`, `pubsub`, `threadLock`, `observability` | |

---

## AgentController methods

`init()`, `initStorage()`, `destroy()`, `createSession({ id?, resourceId?, threadId?, createInitialThread?, ownerId?, tags?, workspace?, browser?, requestContext? })`, `getSession(id)`, `deleteSession({ sessionId })`, `onSessionCreated()`, `onSessionDeleted()`, `listActiveThreadRuns()`, `queryThreads()`, `queryThreadMessages()`, `listModes()`, `getDefaultMode()`, `listAvailableModels()`, `registerInterval()`, `stopIntervals()`.

Channel webhook route: `/api/agent-controllers/<CONTROLLER_ID>/channels/<PLATFORM>/webhook`.

---

## Session API

| Area | Methods |
|---|---|
| Messages | `sendMessage({ content, files?, author? })`, `queueMessage()`, `queueSignal(signal)`, `steer()`, `followUp()`, `abort()`, `getCurrentRunId()` |
| Events | `subscribe(listener)` returns unsubscribe. Events include `message_start`, `message_update`, `message_end`, `tool_approval_required`, `tool_suspended`, `display_state_changed`. |
| Approvals | `respondToToolApproval({ toolCallId, decision: 'approve' \| 'decline' \| 'always_allow_category' })`, `respondToToolSuspension({ toolCallId \| address, resumeData })` |
| Thread | `thread.create/rename/clone/switch/delete/list/getById/listMessages/getOwner/transferOwnership/getSetting/setSetting` |
| Mode / model | `mode.get/resolve/switch({ modeId })`, `model.get/set/switch(modelId)` |
| Permissions | `permissions.setForCategory({ category, policy })`, `permissions.setForTool({ toolName, policy })`, policy `allow \| ask \| deny` |
| Subagents | `subagents.model.get/set({ modelId, agentType? })` |
| State | `state.get()`, `state.set(updates)`, `state.update(fn)`, `displayState.get()` |
| OM | `om.observer.model()/switchModel()`, same for `reflector` |

`submit_plan` resumes with `{ action: 'approved' }` or `{ action: 'rejected', feedback }`.

Client (`@mastra/client-js`): `client.getAgentController(key).session(id)` with `create()`, `subscribe({ onEvent, onError, onReconnect, reconnect })`, `sendMessage()`, `approveTool(id, approved)`, `respondToToolSuspension(id, data)`, `state()`, `listMessages(threadId, { page, perPage, orderBy, filter })`.

---

## Coding agent

`createCodingAgent(config)` from `@mastra/core/coding-agent` accepts all `AgentConfig` fields plus:

| Field | Default when omitted | Opt out |
|---|---|---|
| `workspace` | `LocalFilesystem` + `LocalSandbox` at `basePath` (`process.cwd()`) | `workspace: undefined` |
| `signals` | `TaskSignalProvider` merged in, only with `memory` | Omit memory |
| `errorProcessors` | Stream retry policies, `PrefillErrorHandler`, `ProviderHistoryCompat`, `CyberRefusalHandler` | `errorProcessorDefaults: false` |
| `outputProcessors` | `CyberRefusalHandler` | `outputProcessors: []` |
| `maxProcessorRetries` | 3 | `0` |
| `goal.prompt` | `DEFAULT_GOAL_JUDGE_PROMPT` when `goal` set | Pass your own |

`buildBasePrompt(context)` takes `projectPath`, `projectName`, `gitBranch`, `platform`, `commonBinaries`, `date`, `mode`, `modelId`, `activePlan`, `toolGuidance`, `productName` (default `Mastra Code`), `coAuthorName`, `coAuthorEmail`. Returns a string.

---

## Code SDK

`mountAgentControllerOnMastra({ cwd?, coAuthor?, mastra?, controllerId?, modes?, subagents?, extraTools?, postToolObserver?, inputProcessors?, disabledTools?, disableBuiltinTools?, storage?, workspace?, configDir?, mcpServers?, buildApiRoutes?, buildServerConfig? })` from `@mastra/code-sdk` returns `{ mastra, controller, authStorage }`. Default modes `build/plan/fast`. Pass `[...builtinSubagents]` for explore, plan, and execute subagents. `prepareAgentControllerMount()` returns constructor args plus `finalize()`.

ACP server: run `mastracode --acp`, or `acpMain({ dangerousAutoApprove?, coAuthor? })` from `@mastra/code-sdk/acp/index`. Supports ACP v1 sessions, text prompts, permissions, cancellation, config options, and `/skill/<name>` commands. No session loading, no image prompts.

---

## Workers

| Env var | Purpose |
|---|---|
| `MASTRA_WORKERS` | unset (auto), `false`, `orchestration`, `scheduler`, `backgroundTasks`, or comma list |
| `MASTRA_STEP_EXECUTION_URL` | API base URL for a separate orchestration worker |
| `MASTRA_WORKER_AUTH_TOKEN` | Bearer token for step execution |

| Worker | Notes |
|---|---|
| `orchestration` | Consumes `workflows` topic. Needs pull-capable PubSub. |
| `scheduler` | Polls schedules. Run exactly one. |
| `backgroundTasks` | Consumes `background-tasks`. Scales horizontally. |

Storage with workflows, background tasks, and schedules domains: `@mastra/pg`, `@mastra/libsql`, `@mastra/mysql`, `@mastra/mongodb`, `@mastra/spanner`, `@mastra/convex`.
