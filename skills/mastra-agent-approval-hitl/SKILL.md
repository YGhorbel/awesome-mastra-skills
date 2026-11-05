---
name: mastra-agent-approval-hitl
description: "Pause Mastra agent tool calls for a human: pre-execution approval with requireApproval and requireToolApproval, approve or decline with approveToolCall, declineToolCall, and their generate variants, runtime suspension with suspend() plus suspendSchema and resumeSchema, resumeStream and resumeGenerate, automatic resumption from the next chat message, askUserTool, listSuspendedRuns after a restart, and approvals that bubble up through supervisor agents. Use this skill whenever the user wants a person to confirm, reject, or supply data before an agent action runs, such as deleting records, sending email, issuing refunds, or spending money. Triggers on human-in-the-loop, HITL, tool approval, requireApproval, requireToolApproval, beforeApproval, tool-call-approval, tool-call-suspended, approveToolCall, declineToolCall, resumeStream, resumeGenerate, suspend, autoResumeSuspendedTools, listSuspendedRuns, snapshot not found. Also triggers for confirmation dialogs and approval UIs."
license: Apache-2.0
metadata:
  category: agents
  catalog_summary: "Tool approval, suspend and resume, auto-resume, listSuspendedRuns, and approvals through supervisor agents"
  display_order: 5
  docs: https://mastra.ai/docs/agents/human-in-the-loop
---

# Mastra Agent Approval and Human-in-the-Loop

Pause an agent's tool calls for a human decision or answer, then continue the same run.

---

## When to use

- Destructive or irreversible tools: deletes, emails, payments, refunds
- Costly tools where a human should check the arguments first
- Tools that discover mid-run that they need a confirmation or extra data
- Asking the user a clarifying question from inside a run (`askUserTool`)
- Approval UIs that must survive a page refresh, restart, or load balancer
- Supervisor agents whose subagents call gated tools

## When NOT to use

- Writing the tool itself, schemas, and `execute` (use `mastra-tools`)
- Blocking calls by policy with no human (use `mastra-tools`: `hooks.beforeToolCall`, or `mastra-processors-guardrails`)
- Suspending workflow steps for human input (use `mastra-workflow-suspend-resume`)
- Supervisor and subagent design (use `mastra-multi-agent`)
- Rendering approval cards with AI SDK `useChat()` (use `mastra-agentic-ui`)
- Configuring the storage that holds snapshots (use `mastra-storage`)
- Scoring whether a call is risky with a decision model (use `mastra-classifier`)

---

## Required inputs

- Which tools need approval: always, by name pattern, or by runtime condition
- Whether the human approves a fixed call or supplies data (approval vs `suspend()`)
- The approval channel: stream UI, `generate()` API, webhook, or chat message
- Whether approvals must survive restarts (persistent storage, memory thread ids)
- Whether a supervisor agent sits above the tool's agent

---

## The framework: two ways to pause

| | Pre-execution approval | Runtime suspension |
|---|---|---|
| Set by | `requireApproval: true` on the tool, or `requireToolApproval` on the call | `suspend()` inside `execute` |
| Pauses | Before `execute` runs | Wherever `execute` calls `suspend()` |
| Stream chunk | `tool-call-approval` | `tool-call-suspended` |
| `generate()` | `finishReason: 'suspended'` | `finishReason: 'suspended'` |
| Continue (stream) | `approveToolCall` / `declineToolCall` | `resumeStream(resumeData, { runId })` |
| Continue (generate) | `approveToolCallGenerate` / `declineToolCallGenerate` | `resumeGenerate(resumeData, { runId })` |
| Payload | `toolCallId`, `toolName`, `args` | Your `suspendSchema` shape |
| Auto-resume from chat | No | Yes, with `autoResumeSuspendedTools` |

All of this uses snapshots. Configure a storage provider on the Mastra instance, or you get "snapshot not found".

### Approval

```typescript
import { Agent } from '@mastra/core/agent'
import { createTool } from '@mastra/core/tools'
import { z } from 'zod'

const deleteTool = createTool({
  id: 'delete-record',
  description: 'Delete a record by ID',
  inputSchema: z.object({ id: z.string() }),
  outputSchema: z.object({ deleted: z.boolean() }),
  requireApproval: true,
  execute: async ({ id }) => {
    await db.delete(id)
    return { deleted: true }
  },
})

const agent = new Agent({
  id: 'my-agent',
  name: 'My Agent',
  instructions: 'You manage records.',
  model: 'openai/gpt-6-luna',
  tools: { deleteTool },
})

const stream = await agent.stream('Delete record abc-123')

for await (const chunk of stream.fullStream) {
  if (chunk.type === 'tool-call-approval') {
    const { toolCallId, toolName, args } = chunk.payload
    const approved = await agent.approveToolCall({ runId: stream.runId, toolCallId })
    for await (const c of approved.textStream) process.stdout.write(c)
  }
}
```

Decline with a reason so the model adjusts instead of retrying blindly:

```typescript
await agent.declineToolCall({ runId: stream.runId, toolCallId, reason: 'Ask the user for their own email instead' })
```

### Suspension

```typescript
const weatherTool = createTool({
  id: 'get-weather',
  description: 'Gets the weather for a city',
  inputSchema: z.object({ location: z.string().optional() }),
  suspendSchema: z.object({ question: z.string() }),
  resumeSchema: z.object({ location: z.string() }),
  execute: async ({ location }, context) => {
    const { resumeData, suspend } = context?.agent ?? {}
    const city = resumeData?.location ?? location
    if (!city) {
      return suspend?.({ question: 'Which city would you like the weather for?' })
    }
    return await fetchWeather(city)
  },
})

// later: await agent.resumeStream({ location: 'London' }, { runId })
```

`suspend()` does not throw. Always `return` it, or the code after it runs before the tool pauses.

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/` and the installed `Agent` types. Otherwise fetch `https://mastra.ai/docs/agents/human-in-the-loop.md` and `https://mastra.ai/reference/agents/listSuspendedRuns.md`. Trust these over memory.
2. **Configure storage** on `new Mastra({ storage })`. Use a persistent store if approvals can outlive the process (see `mastra-storage`).
3. **Pick the mechanism per tool.** Fixed confirmation: `requireApproval: true`. Needs user data or a conditional check: `suspend()` with `suspendSchema` and `resumeSchema`. Open question: `askUserTool`.
4. **Add per-call gating if needed.** `requireToolApproval: true` gates everything. A function `({ toolName, args, requestContext, workspace }) => boolean` gates selectively.
5. **Reject early without a human** when policy can decide: `beforeApproval` on the tool returns `{ proceed: false, output }`.
6. **Handle the pause** in the caller: `tool-call-approval` / `tool-call-suspended` chunks, or `finishReason: 'suspended'` from `generate()`.
7. **Continue the run** with the matching method and the `runId`. Pass `toolCallId` whenever several calls can be pending.
8. **Make it restart-safe.** Use memory thread and resource ids, then `listSuspendedRuns({ threadId, resourceId })` in the handler that receives the decision.
9. **Enable chat-driven resume** with `autoResumeSuspendedTools: true` (memory and `resumeSchema` required) for conversational suspend flows.
10. **Test** approve, decline, and resume paths in Studio and after a server restart.

---

## Deep dive: supervisors and restarts

When a subagent's tool needs approval or suspends, the pause bubbles up to the top supervisor, through any depth. The chunk's `toolCallId` is the supervisor's delegation call. Pass that id to approve, decline, or resume. Read `delegatedToolName` and `delegatedToolCallId` to label which subagent tool paused.

```typescript
for await (const chunk of stream.fullStream) {
  if (chunk.type === 'tool-call-approval' || chunk.type === 'tool-call-suspended') {
    console.log('Paused:', chunk.payload.delegatedToolName, chunk.payload.delegatedToolCallId)
    await supervisorAgent.approveToolCall({ runId: stream.runId, toolCallId: chunk.payload.toolCallId })
  }
}
```

After a restart, rediscover the run from storage:

```typescript
const { runs } = await agent.listSuspendedRuns({ threadId: 'thread-123', resourceId: 'user-456' })
const run = runs[0]
const toolCall = run?.toolCalls[0]

if (run && toolCall) {
  const stream = toolCall.requiresApproval
    ? await agent.approveToolCall({ runId: run.runId, toolCallId: toolCall.toolCallId })
    : await agent.resumeStream({ location: 'San Francisco' }, { runId: run.runId })
}
```

`listSuspendedRuns()` only returns runs owned by the agent you call it on. A supervisor sees its outer run. HTTP: `GET /agents/:agentId/suspended-runs`. Client SDK: `agent.listSuspendedRuns()`.

---

## Failure patterns

- **"snapshot not found".** No storage on the Mastra instance. Add one.
- **Approvals lost after deploy or refresh.** In-memory storage drops snapshots. Use a persistent store and `listSuspendedRuns()`.
- **Code runs after `suspend()`.** It does not throw. Use `return suspend?.({...})`.
- **Wrong tool resumed.** Without `toolCallId`, the most recent suspended call resumes. Pass it, especially for supervisors.
- **Using the subagent's tool call id at the supervisor.** Use the chunk's `toolCallId` (the delegation call). `delegatedToolCallId` is for display only.
- **Expecting auto-resume to approve.** `autoResumeSuspendedTools` only resumes `suspend()` flows. Approval-gated tools still need an explicit approve or decline.
- **Auto-resume does nothing.** Missing memory, a different thread or resource id, or no `resumeSchema` on the tool.
- **Function `requireToolApproval` on a durable or stored agent.** Functions cannot be serialized, so every call requires approval. Use a boolean there.
- **`requireApproval: false` on a tool to opt out.** It does not override `requireToolApproval`. A tool-level function is authoritative.
- **Approved arguments drift before execution.** Fingerprint `toolName` and `args` at review time and check it in `hooks.beforeToolCall` (see `references/examples.md`).
- **Client tools inside a subagent.** Subagents cannot run them. Use `suspend()` instead, which propagates to the supervisor.
- **Inferring "answered" from tool output.** Use the `tool-call-resumed` chunk (`payload.kind` is `'approval'` or `'suspension'`).

---

## Output format

A finished HITL delivery contains:

- Gated tools with `requireApproval` or `suspend()` plus `suspendSchema` and `resumeSchema`
- Storage configured on the Mastra instance, persistent for production
- A caller or route that detects the pause and exposes approve, decline, or resume actions
- Restart-safe resume through `listSuspendedRuns()` or the client SDK
- Decline reasons passed back to the model
- Tests or Studio runs covering approve, decline, resume, and restart

---

## Reference files

- [`references/api.md`](references/api.md) - Flags, chunk payloads, approve, decline, and resume methods, `listSuspendedRuns()` types.
- [`references/examples.md`](references/examples.md) - `generate()` approval API, conditional approval, argument-bound approvals, conversational auto-resume, supervisor approval, `askUserTool`.
- [`references/checklist.md`](references/checklist.md) - HITL production checklist.

**Live docs**

- https://mastra.ai/docs/agents/human-in-the-loop
- https://mastra.ai/reference/agents/listSuspendedRuns
- https://mastra.ai/reference/tools/ask-user-tool
- https://mastra.ai/reference/tools/create-tool
- https://mastra.ai/reference/agents/generate
