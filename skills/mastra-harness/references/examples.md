# Harness examples

All examples follow the current docs. Durable agents and workers are beta, so check the installed version.

## Contents

1. Reconnectable durable agent across replicas
2. Background research tool with untilIdle
3. Goal-driven worker agent
4. Coding agent with task tracking and a goal
5. Approvals and plan submission in an AgentController session

---

## 1. Reconnectable durable agent across replicas

```typescript
// src/mastra/agents/researcher.ts
import { Agent } from '@mastra/core/agent'
import { createDurableAgent } from '@mastra/core/agent/durable'
import { RedisServerCache } from '@mastra/redis'
import Redis from 'ioredis'

const agent = new Agent({
  id: 'researcher',
  name: 'Researcher',
  instructions: 'You research topics thoroughly.',
  model: 'openai/gpt-6.1-sol',
})

export const durableResearcher = createDurableAgent({
  agent,
  cache: new RedisServerCache({ client: new Redis(process.env.REDIS_URL!) }),
})
```

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { PostgresStore } from '@mastra/pg'
import { RedisStreamsPubSub } from '@mastra/redis-streams'
import { durableResearcher } from './agents/researcher'

export const mastra = new Mastra({
  agents: { durableResearcher },
  storage: new PostgresStore({ id: 'mastra-storage', connectionString: process.env.DATABASE_URL! }),
  pubsub: new RedisStreamsPubSub({ url: process.env.REDIS_URL, keyPrefix: 'mastra:my-app' }),
  recovery: { durableAgents: 'auto' },
})
```

```typescript
// Start a run, return the runId to the client
const { runId } = await durableResearcher.stream('Research quantum computing advances')

// Reconnect handler, possibly on another replica
export async function reconnect(runId: string, request: Request) {
  const { output, detach } = await durableResearcher.observe(runId, { idleTimeoutMs: 30_000 })
  request.signal.addEventListener('abort', detach, { once: true })
  for await (const chunk of output.fullStream) {
    // forward chunk to the client
  }
}

// Stop a run from any process sharing the PubSub
durableResearcher.abortRunStream(runId)
```

---

## 2. Background research tool with untilIdle

```typescript
// src/mastra/tools/research-tool.ts
import { createTool } from '@mastra/core/tools'
import { z } from 'zod'

export const researchTool = createTool({
  id: 'research',
  description: 'Run a long research job',
  inputSchema: z.object({ topic: z.string() }),
  background: {
    enabled: true,
    defaultDisposition: 'deferred',
    timeoutMs: 600_000,
    maxRetries: 1,
  },
  execute: async ({ topic }) => {
    // Run the research job for topic
    return { summary: `Findings about ${topic}` }
  },
})
```

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { Agent } from '@mastra/core/agent'
import { LibSQLStore } from '@mastra/libsql'
import { Memory } from '@mastra/memory'
import { researchTool } from './tools/research-tool'

const storage = new LibSQLStore({ id: 'storage', url: 'file:mastra.db' })

const researcher = new Agent({
  id: 'researcher',
  name: 'Researcher',
  instructions: 'Start research with the research tool, tell the user it is running, then report results.',
  model: 'openai/gpt-6.1-sol',
  memory: new Memory({ storage }),
  tools: { researchTool },
})

export const mastra = new Mastra({
  agents: { researcher },
  storage,
  backgroundTasks: { enabled: true, globalConcurrency: 10, perAgentConcurrency: 5, defaultTimeoutMs: 300_000 },
})

const stream = await mastra.getAgentById('researcher').stream('Research solana for me', {
  memory: { thread: 't1', resource: 'u1' },
  untilIdle: true,
})

for await (const chunk of stream.fullStream) {
  // includes the follow-up turn after the task completes
}
```

Without `untilIdle`, Mastra sends the agent a `background-task` notification signal on the thread when the task finishes.

---

## 3. Goal-driven worker agent

```typescript
import { Agent } from '@mastra/core/agent'
import { Memory } from '@mastra/memory'
import { LibSQLStore } from '@mastra/libsql'

const memory = new Memory({ storage: new LibSQLStore({ id: 'storage', url: 'file:./mastra.db' }) })

const worker = new Agent({
  id: 'worker',
  name: 'worker',
  instructions: 'You complete software tasks end to end.',
  model: 'openai/gpt-6.1-sol',
  memory,
  goal: {
    judge: 'openai/gpt-6-luna',
    maxRuns: 30,
    prompt: 'Only mark the goal complete when tests pass.',
  },
})

const threadId = 'thread-1'
const resourceId = 'user-1'

await worker.setObjective('Add and test a /health endpoint', { threadId, resourceId })

const stream = await worker.stream('Start working on the goal', {
  memory: { thread: threadId, resource: resourceId },
})

for await (const chunk of stream.fullStream) {
  if (chunk.type === 'goal') console.log(chunk)
}

const record = await worker.getObjective({ threadId })
// If paused after maxRuns:
await worker.updateObjectiveOptions({ threadId, maxRuns: 100 })
```

---

## 4. Coding agent with task tracking and a goal

```typescript
import { createCodingAgent, buildBasePrompt } from '@mastra/core/coding-agent'
import { Memory } from '@mastra/memory'

const instructions = buildBasePrompt({
  projectPath: process.cwd(),
  projectName: 'my-app',
  gitBranch: 'main',
  platform: process.platform,
  date: new Date().toDateString(),
  mode: 'build',
  modelId: 'openai/gpt-5.6',
  toolGuidance: '',
})

export const codingAgent = createCodingAgent({
  id: 'my-coding-agent',
  name: 'My Coding Agent',
  model: 'openai/gpt-5.6',
  instructions,
  basePath: '/srv/checkouts/my-app',
  memory: new Memory(), // adds TaskSignalProvider: task_write, task_update, task_complete, task_check
  goal: { judge: 'openai/gpt-6-luna', maxRuns: 50 },
})

await codingAgent.setObjective('Get the test suite passing', { threadId: 'thread-1', resourceId: 'user-1' })
```

The default workspace runs commands on the host. Pass a `workspace` with a remote sandbox for untrusted code (see `mastra-workspace-sandbox`).

---

## 5. Approvals and plan submission in an AgentController session

Continues from example 4 (`codingAgent`). Pass `workspace: undefined` to `createCodingAgent` if the controller supplies the workspace instead.

```typescript
import { AgentController } from '@mastra/core/agent-controller'
import { LibSQLStore } from '@mastra/libsql'

const storage = new LibSQLStore({ id: 'agent-controller-storage', url: 'file:./mastra.db' })

const controller = new AgentController({
  id: 'coding-controller',
  agent: codingAgent,
  storage,
  modes: [
    { id: 'plan', name: 'Plan', metadata: { default: true }, transitionsTo: 'build', instructions: 'Investigate and propose a plan.' },
    { id: 'build', name: 'Build', instructions: 'Implement the approved plan.' },
  ],
  toolCategoryResolver: toolName => (toolName === 'delete_project' ? 'execute' : null),
})

await controller.init()
const session = await controller.createSession({ resourceId: 'user-123' })

await session.permissions.setForCategory({ category: 'execute', policy: 'ask' })

session.subscribe(event => {
  if (event.type === 'tool_approval_required') {
    session.respondToToolApproval({ toolCallId: event.toolCallId, decision: 'approve' })
  }
  if (event.type === 'tool_suspended' && event.toolName === 'submit_plan') {
    void session.respondToToolSuspension({ toolCallId: event.toolCallId, resumeData: { action: 'approved' } })
  }
})

await session.sendMessage({ content: 'Add rate limiting to the API.' })
```

`submit_plan` takes a plan file path, so the workspace filesystem must be writable. Approving switches the session to the `transitionsTo` mode.
