---
name: mastra-agents
description: "Build, configure, register, and call Mastra agents: the Agent class, instructions, model router strings, tools, subagents, memory, dynamic configuration through RequestContext, and generate() or stream() calls. Use this skill whenever the user wants to create an AI agent with Mastra, write or fix a new Agent({...}) definition, call agent.generate or agent.stream, tune maxSteps or stopWhen, add model fallbacks, or make instructions, model, or tools depend on the user or tenant. Triggers on Mastra agent, @mastra/core/agent, new Agent, mastra.getAgentById, agent.generate, agent.stream, agent instructions, system prompt, defaultOptions, requestContext, dynamic instructions, agent hooks, model fallback. Also triggers for any open-ended LLM task in a Mastra project where the steps are not known in advance, even if the user does not say agent."
license: Apache-2.0
metadata:
  category: agents
  catalog_summary: "Agent class, instructions, model strings, registration, generate and stream, dynamic config, fallbacks"
  display_order: 1
  docs: https://mastra.ai/docs/agents/overview
---

# Mastra Agents

Define a Mastra agent, register it, and call it correctly. Agents use an LLM plus tools to solve open-ended tasks, looping until the model gives a final answer or a stop condition fires.

---

## When to use

- Creating a new agent or reviewing an existing `new Agent({...})` definition
- Calling an agent with `.generate()` or `.stream()` from code, a route, a workflow step, or a tool
- Writing or restructuring agent instructions (system prompts)
- Making instructions, model, tools, or memory depend on the request (tenant, tier, locale)
- Adding model fallbacks, step limits, or default execution options
- Deciding between an agent and a workflow

## When NOT to use

- Defining the tools an agent calls (use `mastra-tools`)
- Typed JSON responses (use `mastra-structured-output`)
- Supervisor agents, subagents, and delegation (use `mastra-multi-agent`)
- Conversation history and threads (use `mastra-memory`)
- Tool approval and pausing for a human (use `mastra-agent-approval-hitl`)
- Input or output filtering, PII, prompt injection (use `mastra-processors-guardrails`)
- Fixed, known sequences of steps (use `mastra-workflows`)
- Agents defined as files instead of TypeScript classes (use `mastra-file-based-agents`)
- Choosing a provider or model ID (use `mastra-models`)

---

## Required inputs

- The agent's job: one sentence on the goal and what "done" looks like
- The model (a `provider/model` string, verified with `mastra-models`)
- The tools, subagents, or workflows it may use, if any
- Whether it needs memory (multi-turn conversation) and who owns each thread
- Anything that varies per request (user tier, tenant, locale, feature flags)

Elicit missing items before writing code. Default to no memory and no tools if the user only wants a single-turn assistant.

---

## The framework: define, register, call

### 1. Define

```typescript
// src/mastra/agents/support-agent.ts
import { Agent } from '@mastra/core/agent'
import { lookupOrderTool } from '../tools/lookup-order-tool'

export const supportAgent = new Agent({
  id: 'support-agent',
  name: 'Support Agent',
  description: 'Answers order and shipping questions', // used when this agent is a subagent
  instructions: `
    You help customers with order questions.
    Use lookupOrderTool to fetch order status before answering.
    If the order is not found, ask for the order number.`,
  model: 'openai/gpt-6.1-sol',
  tools: { lookupOrderTool },
})
```

Required: `id`, `name`, `instructions`, `model`. Everything else is optional: `description`, `tools`, `agents`, `workflows`, `memory`, `defaultOptions`, `inputProcessors`, `outputProcessors`, `scorers`, `voice`, `hooks`, `requestContextSchema`.

### 2. Register

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { supportAgent } from './agents/support-agent'

export const mastra = new Mastra({ agents: { supportAgent } })
```

Registration gives the agent shared storage, logging, tracing, and the agent registry. It also exposes it in Studio and over the server API.

### 3. Call

```typescript
const agent = mastra.getAgentById('support-agent')

const result = await agent.generate('Where is order 1234?')
console.log(result.text, result.toolCalls, result.usage)

const stream = await agent.stream('Where is order 1234?')
for await (const chunk of stream.textStream) process.stdout.write(chunk)
```

Fetch through `mastra.getAgentById()`, not a direct import, so the agent gets instance-level services.

### Agent vs workflow

| Choose an agent when | Choose a workflow when |
|---|---|
| Steps are not known in advance | Steps and order are known |
| The model should pick tools and loop | You need explicit branching, parallelism, retries |
| Output is conversational | You need suspend/resume at fixed points |

Agents and workflows compose: an agent can call a workflow as a tool, and a workflow step can call an agent.

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read `node_modules/@mastra/core/dist/docs/` and the installed `Agent` types. Otherwise fetch `https://mastra.ai/docs/agents/overview.md` and `https://mastra.ai/reference/agents/agent.md`. Trust these over memory.
2. **Pick the model.** Use a `provider/model` string. Confirm the ID and its env var with `mastra-models` (for example `OPENAI_API_KEY`).
3. **Write instructions.** Role, goal, tool usage rules ("Use X to ..."), constraints, and output style. Name each tool and when to call it.
4. **Attach capabilities.** Tools (`mastra-tools`), subagents (`mastra-multi-agent`), workflows as tools, memory (`mastra-memory`).
5. **Make it dynamic if needed.** Turn `instructions`, `model`, `tools`, or `memory` into functions of `{ requestContext }`. Add `requestContextSchema` to fail fast on missing keys.
6. **Set execution defaults.** Put `maxSteps`, `modelSettings`, and similar options in `defaultOptions`. Add a model fallback array for resilience.
7. **Register** the agent in `src/mastra/index.ts`.
8. **Test** in Studio (`npx mastra dev`, open `http://localhost:4111`) or with `npx mastra api agent run <agent-id> '{"messages":"<message>"}'` (see `mastra-cli-api`).
9. **Add evals and tracing** before production (`mastra-evals`, `mastra-observability`).

---

## Deep dive: dynamic configuration

Every major field accepts a function of `{ requestContext }`, sync or async.

```typescript
import { Agent } from '@mastra/core/agent'
import { z } from 'zod'

export const tieredAgent = new Agent({
  id: 'tiered-agent',
  name: 'Tiered Agent',
  requestContextSchema: z.object({ tier: z.enum(['free', 'pro']), locale: z.string() }),
  instructions: ({ requestContext }) => {
    const { tier, locale } = requestContext.all
    const base = tier === 'pro' ? 'Give detailed, technical answers.' : 'Be brief and friendly.'
    return `${base} Reply in the language for locale ${locale}.`
  },
  model: ({ requestContext }) =>
    requestContext.get('tier') === 'pro' ? 'anthropic/claude-opus-5-5' : 'openai/gpt-6-luna',
})
```

Set the values at call time:

```typescript
import { RequestContext } from '@mastra/core/request-context'

const requestContext = new RequestContext()
requestContext.set('tier', 'pro')
requestContext.set('locale', 'fr-FR')
await mastra.getAgentById('tiered-agent').generate('Explain retries', { requestContext })
```

On a Mastra server, populate `requestContext` from headers or auth in middleware (see `mastra-server`).

---

## Failure patterns

- **`openai:gpt-...` or importing a provider object.** Use the router string `'openai/gpt-6.1-sol'`. The colon form is wrong.
- **Calling a directly imported agent in production code.** It misses instance storage, logger, and tracing. Use `mastra.getAgentById()`.
- **Forgetting registration.** The agent will not appear in Studio or the API. Add it to `new Mastra({ agents })`.
- **Instructions that never mention the tools.** The model under-uses them. Name each tool and the condition for calling it.
- **Empty final answer after hitting `maxSteps`.** The last step was a tool call. Raise `maxSteps`, or add the final-step reminder processor (see `mastra-processors-guardrails`).
- **Using `maxTokens`.** The setting is `modelSettings.maxOutputTokens`.
- **Per-request logic with `if` statements at module load.** Move it into a `({ requestContext }) => ...` function.
- **Missing env var for the provider.** Errors look like auth failures. Check `mastra-models` for the variable name.
- **Old method names** such as `generateLegacy`/`streamLegacy` in new code. Use `generate()` and `stream()`. See `mastra-migrations` when upgrading.
- **Too many tools on one agent.** Tool choice degrades. Split into subagents or use the tool search processor.

---

## Output format

A finished agent delivery contains:

- `src/mastra/agents/<agent-id>.ts` exporting the agent
- Registration in `src/mastra/index.ts`
- Required env vars listed in `.env.example` (never commit `.env`)
- A short usage snippet (`generate` or `stream`) or route handler
- Evidence it works: a Studio run, a `mastra api` call, or a test

---

## Reference files

- [`references/api.md`](references/api.md) - Constructor options, `generate()`/`stream()` options, and response fields.
- [`references/examples.md`](references/examples.md) - Complete agents: basic, tool-using, dynamic multi-tenant, fallback models, stop conditions.
- [`references/checklist.md`](references/checklist.md) - Pre-production checklist for an agent.

**Live docs**

- https://mastra.ai/docs/agents/overview
- https://mastra.ai/reference/agents/agent
- https://mastra.ai/reference/agents/generate
- https://mastra.ai/reference/streaming/agents/MastraModelOutput
- https://mastra.ai/docs/server/request-context
