# Human-in-the-loop checklist

Run this before calling an approval flow done.

## Setup

- [ ] Storage configured on `new Mastra({ storage })`
- [ ] Persistent storage (not in-memory) for any approval that can outlive the process
- [ ] Every destructive, irreversible, or costly tool is gated
- [ ] Each gated tool uses the right mechanism: `requireApproval`, `suspend()`, or `askUserTool`
- [ ] `suspend()` tools define `suspendSchema` and `resumeSchema`
- [ ] Every `suspend()` call is returned (`return suspend?.({...})`)
- [ ] `beforeApproval` rejects calls that policy can decide without a human

## Caller

- [ ] Stream callers handle `tool-call-approval` and `tool-call-suspended`
- [ ] `generate()` callers handle `finishReason: 'suspended'`
- [ ] Approve, decline, and resume pass `toolCallId` when several calls can be pending
- [ ] Declines pass a `reason` the model can act on
- [ ] UI marks questions answered from `tool-call-resumed`, not from tool output shape

## Durability

- [ ] Calls use memory `thread` and `resource` ids
- [ ] Decision handlers rediscover runs with `listSuspendedRuns({ threadId, resourceId })`
- [ ] Browser UIs use the client SDK `agent.listSuspendedRuns()` or `GET /agents/:agentId/suspended-runs`
- [ ] Auto-resume only where memory and `resumeSchema` exist

## Supervisors

- [ ] Approvals are answered at the top supervisor with the chunk's `toolCallId`
- [ ] UI labels pauses with `delegatedToolName`
- [ ] Subagents use `suspend()` instead of client tools

## Safety

- [ ] Sensitive approvals are bound to a fingerprint of `toolName` and `args`
- [ ] Function-based `requireToolApproval` is not used on durable or stored agents
- [ ] Classifier-based gating sends only the data the decision needs

## Verification

- [ ] Approve, decline, and resume paths tested
- [ ] Resume tested after a server restart
- [ ] Supervisor path tested if subagents call gated tools
