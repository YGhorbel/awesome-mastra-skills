# Agent approval API reference

Distilled from `https://mastra.ai/docs/agents/human-in-the-loop.md`, `https://mastra.ai/reference/agents/listSuspendedRuns.md`, `https://mastra.ai/reference/tools/create-tool.md`, and `https://mastra.ai/reference/agents/generate.md`. Verify against the installed version.

## Contents

- Flags
- Tool options
- Execution context for suspension
- Stream chunks
- generate() results
- Continue methods
- listSuspendedRuns()
- Related agent options

---

## Flags

Combined with OR logic. If either requires approval, the call pauses.

| Flag | Where | Scope |
|---|---|---|
| `requireToolApproval: boolean \| fn` | `stream()` / `generate()` options | Every tool call in the request, or those the function selects |
| `requireApproval: boolean` | `createTool()` | That tool |

`requireToolApproval` function: `({ toolName, args, requestContext, workspace }) => boolean | Promise<boolean>`. Returning `true` pauses for a human; it does not auto-approve. If it throws, approval is required. Not supported on durable or stored agents (they fall back to approving every call).

Precedence: a boolean `requireApproval: false` does not disable approval from `requireToolApproval`. A tool-level `requireApproval` function is authoritative for that tool.

---

## Tool options

| Option | Notes |
|---|---|
| `requireApproval` | Pause before `execute`. Input is validated first; invalid input returns the error to the model with no approval request. |
| `beforeApproval(input, context)` | Runs before the approval gate. `context` has `toolCallId`, `toolName`, `requestContext`, `workspace`. Return `{ proceed: false, output }` to reject with no pause. Not run on invalid input or when resuming. If it throws, the call goes to the gate. |
| `suspendSchema` | Shape of the `suspend()` payload sent to the client. |
| `resumeSchema` | Shape of `resumeData`. Required for auto-resume. |

---

## Execution context for suspension

Inside `execute(inputData, context)`:

| Field | Notes |
|---|---|
| `context.agent.suspend(payload)` | Pauses the run. Does not throw. `return` it. |
| `context.agent.resumeData` | The data passed to `resumeStream`/`resumeGenerate`, or extracted by auto-resume. Undefined on the first run. |

Workflow tools use `context.workflow.suspend` instead (see `mastra-workflow-suspend-resume`).

---

## Stream chunks

| Chunk | Payload |
|---|---|
| `tool-call-approval` | `toolCallId`, `toolName`, `args`, plus `delegatedToolCallId`, `delegatedToolName` when raised from a subagent |
| `tool-call-suspended` | `toolCallId`, `toolName`, `suspendPayload`, plus delegated fields when from a subagent |
| `tool-call-resumed` | Same `toolCallId`, `kind: 'approval' \| 'suspension'`, original `args`, `suspendPayload`, `resumeSchema`. Emitted before the call's `tool-result`. |

With `@mastra/ai-sdk`, these arrive as `data-tool-call-approval` and `data-tool-call-suspended` parts; a resumed part has `resumed: true`.

---

## `generate()` results

When paused, `generate()` returns `finishReason: 'suspended'`, a `runId`, and `suspendPayload`:

- Approval: `suspendPayload.toolCallId`, `suspendPayload.toolName`, `suspendPayload.args`
- `suspend()`: the tool's data is in `suspendPayload.suspendPayload`

---

## Continue methods

| Method | Use |
|---|---|
| `agent.approveToolCall({ runId, toolCallId? })` | Stream. Approve and continue. Returns a stream. |
| `agent.declineToolCall({ runId, toolCallId?, reason? })` | Stream. Decline. `reason` replaces the tool result. |
| `agent.approveToolCallGenerate({ runId, toolCallId? })` | Generate. Returns a full output. |
| `agent.declineToolCallGenerate({ runId, toolCallId?, reason? })` | Generate. |
| `agent.resumeStream(resumeData, { runId })` | Resume a `suspend()` call, or approve with `{ approved: boolean }`. |
| `agent.resumeGenerate(resumeData, { runId })` | Generate variant. |
| `agent.declineNetworkToolCall(...)` | Network variant; also accepts `reason`. |
| `agent.sendToolApproval(...)` | Uses storage-backed discovery when memory has no active run. Pass `toolCallId` when several runs match. |

`toolCallId` is optional on the approve and decline methods. Without it, the most recent suspended call continues. Default decline message: `Tool call was not approved by the user`. The reason is stored on the tool call's `approval` metadata.

---

## `listSuspendedRuns()`

Added in `@mastra/core@1.43.0`.

```typescript
const { runs, total } = await agent.listSuspendedRuns({
  threadId, resourceId, fromDate, toDate, perPage, page,
})
```

```typescript
interface AgentRun {
  runId: string
  status: 'suspended'
  threadId?: string
  resourceId?: string
  suspendedAt: Date
  toolCalls: AgentRunToolCall[]
}

interface AgentRunToolCall {
  toolCallId?: string
  toolName?: string
  args?: unknown // approval suspensions only
  requiresApproval: boolean
  suspendPayload?: unknown // suspend() suspensions
}
```

- Scoped to the agent you call it on. Subagent inner runs are visible only from the subagent.
- Snapshots exist only while waiting and are deleted when the run finishes.
- Pagination applies only when both `perPage` and `page` are set. `page` is zero-indexed.
- `@mastra/pg` and `@mastra/libsql` filter by thread and resource inside the database.
- HTTP: `GET /agents/:agentId/suspended-runs`. Client SDK: `agent.listSuspendedRuns()`.

---

## Related agent options

| Option | Notes |
|---|---|
| `autoResumeSuspendedTools` | Resume `suspend()` tools from the next user message on the same thread. Needs memory and `resumeSchema`. Does not approve `requireApproval` tools. |
| `toolCallConcurrency` | Defaults to 1 when approval may be required, otherwise 10. |
| `hooks.beforeToolCall` | Runs after approval, right before execution. Use it to verify the approved arguments. |
