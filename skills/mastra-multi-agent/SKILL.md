---
name: mastra-multi-agent
description: "Build multi-agent systems in Mastra: supervisor agents with subagents in the agents map, delegation hooks (onDelegationStart, onDelegationComplete, messageFilter), memory isolation, rubric and task-completion loops, and pattern choice between supervisor, workflow, handoff, and council. Use this skill whenever the user wants one agent to delegate to other agents, coordinate specialists, control or reject delegations, filter context passed to subagents, make an agent self-correct until criteria pass, or migrate away from agent.network(). Triggers on supervisor agent, subagents, agents: { ... }, delegation, onDelegationStart, onDelegationComplete, messageFilter, isTaskComplete, createRubricScorer, onIterationComplete, agent.network, routing agent, multi-agent, orchestrator agent, research and writing agents. Also triggers when a single agent has grown too many tools or responsibilities and should be split."
license: Apache-2.0
metadata:
  category: agents
  catalog_summary: "Supervisor agents, subagents, delegation hooks, message filtering, rubric loops, and network() migration"
  display_order: 6
  docs: https://mastra.ai/docs/subagents
---

# Mastra Multi-Agent Systems

Split work across specialist agents and keep one supervisor in control. Mastra exposes each subagent to the supervisor as a tool and gives you hooks to steer every delegation.

---

## When to use

- One agent needs too many tools, too much context, or different prompts per stage
- A task mixes kinds of work (research, writing, review) that benefit from specialists
- The order of steps is not known in advance and a lead agent should decide
- You need to modify, reject, or audit delegations at runtime
- You want an agent to iterate until a checklist (rubric) passes
- Existing code calls `agent.network()` and must move to supervisor agents

## When NOT to use

- A single agent with a few tools is enough (use `mastra-agents`)
- The execution path is fixed and known (use `mastra-workflows`)
- Pausing a subagent's tool for human approval in detail (use `mastra-agent-approval-hitl`)
- Subagents declared as `subagents/` directories (use `mastra-file-based-agents`)
- Long-running delegations as background tasks (use `mastra-harness`)
- Writing or tuning scorers beyond the completion loop (use `mastra-evals`)
- Rendering supervisor streams in a UI (use `mastra-streaming` and `mastra-agentic-ui`)

---

## Required inputs

- The overall task and what "done" means (this becomes the success criteria)
- The specialists: one job per subagent, with its tools and model
- What each subagent returns (bullets, paragraphs, JSON), stated in its `description`
- Whether subagents should see the full conversation or a filtered slice
- Step budgets for the supervisor and each subagent
- Whether memory is needed (supervisor threads, tenant metadata on subagent threads)

---

## The framework: supervisor, subagents, delegation

A supervisor is a normal `Agent` with an `agents` map. Mastra converts each entry into an `agent-<key>` tool. The supervisor model reads each subagent's `description` to decide when to delegate.

```typescript
import { Agent } from '@mastra/core/agent'

const researchAgent = new Agent({
  id: 'research-agent',
  name: 'Research Agent',
  description: 'Gathers factual information and returns bullet-point summaries.',
  instructions: 'Research the topic. Return concise bullet points with sources.',
  model: 'openai/gpt-6-luna',
})

const writingAgent = new Agent({
  id: 'writing-agent',
  name: 'Writing Agent',
  description: 'Transforms research into well-structured articles.',
  instructions: 'Turn research notes into a clear article.',
  model: 'openai/gpt-6-luna',
})

export const supervisor = new Agent({
  id: 'supervisor',
  name: 'Supervisor',
  instructions: `You coordinate research and writing using specialized agents.
    Delegate to research-agent for facts, then writing-agent for content.`,
  model: 'openai/gpt-6.1-sol',
  agents: { researchAgent, writingAgent },
})

const stream = await supervisor.stream('Research AI in education and write an article', {
  maxSteps: 10,
})
for await (const chunk of stream.textStream) process.stdout.write(chunk)
```

### Control points

| Control | Where | Use it to |
|---|---|---|
| `delegation.onDelegationStart` | `stream()`/`generate()` options or `defaultOptions` | Rewrite the prompt, set `modifiedMaxSteps`, reject, add `threadMetadata`, set request context for the subagent |
| `delegation.onDelegationComplete` | same | Inspect result, `bail()`, return `feedback` (next turn) or `resultText` (this run) |
| `delegation.messageFilter` | same | Trim or redact the messages forwarded to the subagent |
| `onIterationComplete` | call options | Log, inject `feedback`, or stop the supervisor loop |
| `isTaskComplete` | call options | Run scorers after each iteration and keep going until they pass |
| `abortSignal` | call options | Cancel the supervisor and in-flight subagents together |

### Pattern choice

| Pattern | Who stays in control | Mastra implementation |
|---|---|---|
| Supervisor | One lead agent | `agents` map plus delegation hooks |
| Workflow | The execution graph | `createWorkflow()` with agent steps |
| Handoff | The current specialist | Agents plus workflows plus memory |
| Council | A final synthesis step | Agents in workflow `.parallel()`, then a synthesis step |

Start with one agent. Add agents only when the split clearly improves quality, speed, or reliability.

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/` and the installed `Agent` types for `agents` and `delegation`. Otherwise fetch `https://mastra.ai/docs/subagents.md` and `https://mastra.ai/reference/agents/generate.md`. Subagents need `@mastra/core@1.8.0` or later. Trust these over memory.
2. **Pick the pattern.** Use the table above. If the path is fixed, stop and use `mastra-workflows`.
3. **Define subagents.** One responsibility each. Write `description` as routing text: what it does, what it returns, when to use it.
4. **Write supervisor instructions.** List available resources, a delegation strategy, and success criteria.
5. **Bound the loop.** Set `maxSteps` on the supervisor call and `defaultOptions.maxSteps` on each subagent. The supervisor model can lower a subagent's budget but not raise it.
6. **Add delegation hooks.** Put shared hooks in the supervisor's `defaultOptions.delegation`. Filter messages when subagents must not see sensitive or bulky context.
7. **Add a completion check** when quality matters: `isTaskComplete` with `createRubricScorer` or a custom scorer.
8. **Register** the supervisor (and the subagents if you call them directly) on `new Mastra({ agents })`.
9. **Test** in Studio and inspect the trace: one span per delegation, the prompt sent, and the result returned.

---

## Deep dive: delegation hooks

```typescript
const stream = await supervisor.stream('Research AI trends', {
  maxSteps: 10,
  delegation: {
    onDelegationStart: async context => {
      if (context.primitiveId === 'research-agent') {
        context.requestContext.set('audience', 'technical')
        return {
          proceed: true,
          modifiedPrompt: `${context.prompt}\n\nFocus on 2024-2025 data.`,
          modifiedMaxSteps: 5,
        }
      }
      if (context.iteration > 8) {
        return { proceed: false, rejectionReason: 'Max iterations reached. Synthesize current findings.' }
      }
      return { proceed: true }
    },
    onDelegationComplete: ({ success }) => {
      if (!success) return { resultText: 'The delegated task failed. Try another approach.' }
    },
    messageFilter: ({ messages }) => messages.slice(-10),
  },
})
```

Rules worth remembering:

- A throwing hook does not fail the delegation by default. Set `hookErrorStrategy: 'throw'` to fail it. Failures are recorded under `requestContext.get('__mastra_delegationHookErrors')`.
- `feedback` is saved to supervisor memory for the next turn. `resultText` changes what the supervisor sees now.
- Prefer a curated `resultText` over forwarding `error.message`. Provider errors can leak sensitive data.
- Subagents get the full parent context unless you filter, but only the delegation prompt and response are saved to their memory, in a fresh thread per delegation.

---

## Failure patterns

- **Subagent never called.** Missing or vague `description`. Describe purpose, return format, and when to use it. Name each subagent in the supervisor instructions.
- **Supervisor loops forever or stops early.** No `maxSteps`. Set it on the call, and give subagents `defaultOptions.maxSteps`.
- **Supervisor cuts a subagent short.** The model passed a low `maxSteps`. Return `modifiedMaxSteps` from `onDelegationStart`.
- **Empty delegation result looks like success.** The subagent stopped on a tool-calls step. Detect it in `onDelegationComplete` and return a `resultText` that says so.
- **Subagent calls a client tool and stalls.** Subagents cannot run tools without `execute`. Give client tools to the supervisor, or use `suspend()` in the subagent's tool.
- **Supervisor restates earlier results and burns tokens.** Set `delegation.enableResultReferences: true` so later delegations reuse results by reference.
- **Hook errors silently ignored.** Default strategy continues. Set `hookErrorStrategy: 'throw'` for hooks that must succeed.
- **Leaking secrets to specialists.** Add a `messageFilter` that redacts or trims history.
- **New code calls `agent.network()`.** It is deprecated. Use `stream()`/`generate()` on a supervisor. See `references/api.md` for the chunk mapping.
- **Rubric never satisfied.** Criteria are vague or not verifiable. Write concrete, checkable criteria and mark nice-to-haves `required: false`.

---

## Output format

A finished multi-agent delivery contains:

- `src/mastra/agents/<subagent-id>.ts` for each specialist, each with `description` and a step budget
- `src/mastra/agents/<supervisor-id>.ts` with `agents`, instructions listing resources and success criteria, and `defaultOptions.delegation` hooks if shared
- Registration in `src/mastra/index.ts`
- A call site with `maxSteps`, and `isTaskComplete` when completion matters
- Evidence: a Studio trace showing each delegation, or a test asserting the final output

---

## Reference files

- [`references/api.md`](references/api.md) - `agents` option, `delegation` config, hook contexts and return values, `isTaskComplete`, `createRubricScorer`, `network()` deprecation map.
- [`references/examples.md`](references/examples.md) - Research supervisor, guarded delegation with filtering, rubric self-correction, council with workflow `.parallel()`.
- [`references/checklist.md`](references/checklist.md) - Pre-production checklist for multi-agent systems.

**Live docs**

- https://mastra.ai/docs/subagents
- https://mastra.ai/docs/guides/multi-agent-systems
- https://mastra.ai/reference/agents/generate
- https://mastra.ai/reference/streaming/agents/stream
- https://mastra.ai/reference/evals/rubric
- https://mastra.ai/reference/agents/network
- https://mastra.ai/reference/migrations/network-to-supervisor
