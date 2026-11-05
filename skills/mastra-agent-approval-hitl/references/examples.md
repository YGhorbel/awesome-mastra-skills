# Agent approval examples

All examples follow the current docs. `db`, `fetchWeather`, `database`, and UI helpers stand in for your own code. Every example needs storage on the Mastra instance.

## Contents

1. Approval over a generate() API
2. Conditional approval with a function and a classifier
3. Bind an approval to the exact arguments
4. Conversational auto-resume
5. Supervisor with a gated subagent tool
6. Ask the user with askUserTool

---

## 1. Approval over a `generate()` API

```typescript
const output = await agent.generate('Find user John', {
  requireToolApproval: true,
})

if (output.finishReason === 'suspended') {
  // Show output.suspendPayload.toolName and .args to a reviewer, then:
  const result = await agent.approveToolCallGenerate({
    runId: output.runId,
    toolCallId: output.suspendPayload.toolCallId,
  })
  console.log(result.text)

  // Or decline:
  // await agent.declineToolCallGenerate({ runId: output.runId, toolCallId: output.suspendPayload.toolCallId })
}
```

For a `suspend()` tool, read `output.suspendPayload.suspendPayload` and continue with `agent.resumeGenerate(resumeData, { runId: output.runId! })`.

---

## 2. Conditional approval with a function and a classifier

Gate by name:

```typescript
const stream = await agent.stream('Clean up old records', {
  requireToolApproval: ({ toolName }) => /^delete_/.test(toolName),
})
```

Gate by a risk estimate from a decision model (see `mastra-classifier`):

```typescript
import { Classifier } from '@mastra/core/classifier'
import { typeSafeAi } from '@ai-sdk/typesafe-ai'

const approvalClassifier = new Classifier({
  id: 'tool-approval-classifier',
  model: typeSafeAi.decisionModel('jev-latest'),
  questions: {
    requiresApproval: {
      type: 'boolean',
      instructions:
        'Does this tool call need human approval because it is destructive, irreversible, expensive, or handles sensitive data?',
    },
  },
})

const stream = await agent.stream('Clean up old records', {
  requireToolApproval: async ({ toolName, args }) => {
    const result = await approvalClassifier.decide({
      state: { toolName, argumentNames: Object.keys(args) },
    })
    // A refusal has no probability, so fall back to requiring approval.
    return (result.answers.requiresApproval.probability ?? 1) >= 0.7
  },
})
```

Send argument names, not values, unless the decision provider meets your data-handling rules.

---

## 3. Bind an approval to the exact arguments

```typescript
import { Agent } from '@mastra/core/agent'

// Use a stable hash in production.
function actionFingerprint(toolName: string, args: unknown) {
  return `fingerprint-${JSON.stringify({ toolName, args })}`
}

const sensitiveTools = new Set(['issue_refund', 'delete_record'])
const approvedFingerprints = new Set<string>()

export const approvalBoundAgent = new Agent({
  id: 'approval-bound-agent',
  name: 'Approval Bound Agent',
  instructions: 'You handle refunds and record cleanup.',
  model: 'openai/gpt-6.1-sol',
  tools: { issueRefundTool, deleteRecordTool },
  hooks: {
    beforeToolCall: ({ toolName, input }) => {
      if (!sensitiveTools.has(toolName)) return
      const fingerprint = actionFingerprint(toolName, input)
      if (!approvedFingerprints.delete(fingerprint)) {
        return { proceed: false, output: `Tool call blocked: approval did not match ${toolName} arguments.` }
      }
    },
  },
})
```

```typescript
const stream = await approvalBoundAgent.stream('Refund order ord-1042', {
  requireToolApproval: ({ toolName }) => sensitiveTools.has(toolName),
})

async function consume(current: typeof stream) {
  for await (const chunk of current.fullStream) {
    if (chunk.type === 'tool-call-approval') {
      const { toolName, toolCallId, args } = chunk.payload
      const fingerprint = actionFingerprint(toolName, args)
      const ok = await showApprovalDialog({ toolName, args, fingerprint })

      if (ok) approvedFingerprints.add(fingerprint)
      const next = ok
        ? await approvalBoundAgent.approveToolCall({ runId: current.runId, toolCallId })
        : await approvalBoundAgent.declineToolCall({ runId: current.runId, toolCallId })
      await consume(next)
    }
  }
}

await consume(stream)
```

In production, store fingerprints durably, scoped to user, run, tool call, and policy version.

---

## 4. Conversational auto-resume

```typescript
import { Agent } from '@mastra/core/agent'
import { createTool } from '@mastra/core/tools'
import { Memory } from '@mastra/memory'
import { z } from 'zod'

const weatherTool = createTool({
  id: 'weather-tool',
  description: 'Fetches weather for a city',
  inputSchema: z.object({ city: z.string() }),
  outputSchema: z.object({ weather: z.string() }),
  suspendSchema: z.object({ message: z.string() }),
  resumeSchema: z.object({ city: z.string() }),
  execute: async (inputData, context) => {
    const { resumeData, suspend } = context?.agent ?? {}
    if (!inputData.city && !resumeData?.city) {
      return suspend?.({ message: 'What city do you want to know the weather for?' })
    }
    const city = resumeData?.city ?? inputData.city
    const response = await fetch(`https://wttr.in/${city}?format=3`)
    return { weather: `${city}: ${await response.text()}` }
  },
})

export const agent = new Agent({
  id: 'my-agent',
  name: 'My Agent',
  instructions: 'You are a helpful assistant',
  model: 'openai/gpt-6-luna',
  tools: { weatherTool },
  memory: new Memory(),
  defaultOptions: { autoResumeSuspendedTools: true },
})
```

```typescript
const memory = { thread: 'thread-123', resource: 'user-456' }
await agent.stream("What's the weather like?", { memory }) // suspends and asks for a city
await agent.stream('San Francisco', { memory }) // extracts { city } and resumes
```

Both messages must use the same thread and resource.

---

## 5. Supervisor with a gated subagent tool

```typescript
import { Agent } from '@mastra/core/agent'
import { createTool } from '@mastra/core/tools'
import { Memory } from '@mastra/memory'
import { z } from 'zod'

const findUserTool = createTool({
  id: 'find-user',
  description: 'Finds user by ID in the database',
  inputSchema: z.object({ userId: z.string() }),
  outputSchema: z.object({ user: z.object({ id: z.string(), name: z.string(), email: z.string() }) }),
  requireApproval: true,
  execute: async input => ({ user: await database.findUser(input.userId) }),
})

const dataAgent = new Agent({
  id: 'data-agent',
  name: 'Data Agent',
  description: 'Handles database queries and user data retrieval',
  instructions: 'Look up users with find-user.',
  model: 'openai/gpt-6-luna',
  tools: { findUserTool },
})

const supervisorAgent = new Agent({
  id: 'supervisor',
  name: 'Supervisor Agent',
  instructions: 'You coordinate data retrieval tasks. Delegate to data-agent for user lookups.',
  model: 'openai/gpt-6.1-sol',
  agents: { dataAgent },
  memory: new Memory(),
})

const output = await supervisorAgent.generate('Find user with ID 12345', { maxSteps: 10 })

if (output.finishReason === 'suspended') {
  const result = await supervisorAgent.approveToolCallGenerate({
    runId: output.runId,
    toolCallId: output.suspendPayload.toolCallId, // the supervisor's delegation call
  })
  console.log(result.text)
}
```

---

## 6. Ask the user with `askUserTool`

```typescript
import { Agent } from '@mastra/core/agent'
import { askUserTool } from '@mastra/core/tools'

const assistant = new Agent({
  id: 'assistant',
  name: 'Assistant',
  instructions: 'Ask the user for clarification when the request is ambiguous.',
  model: 'openai/gpt-6.1-sol',
  tools: { askUserTool },
})

const stream = await assistant.stream('Summarize my project')

for await (const chunk of stream.fullStream) {
  if (chunk.type === 'tool-call-suspended') {
    const { question, options, selectionMode } = chunk.payload.suspendPayload
    const answer = await getUserAnswer({ question, options, selectionMode }) // string or string[]
    const resumed = await assistant.resumeStream(answer, { runId: stream.runId })
    for await (const c of resumed.textStream) process.stdout.write(c)
  }
}
```

Multi-select prompts resume with a `string[]`. See `mastra-tools` for `submitPlanTool`, which follows the same pattern with `{ action: 'approved' | 'rejected', feedback? }`.
