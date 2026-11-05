# Agent examples

All examples follow the current docs. Model IDs come from `https://mastra.ai/models`. Verify before copying into a project on an older version.

## Contents

1. Minimal agent, registered and called
2. Agent with tools and a workflow
3. Multi-tenant agent with validated request context
4. Resilient agent with model fallbacks and defaults
5. Steering the loop with onIterationComplete
6. Prompt caching with provider options

---

## 1. Minimal agent, registered and called

```typescript
// src/mastra/agents/assistant.ts
import { Agent } from '@mastra/core/agent'

export const assistant = new Agent({
  id: 'assistant',
  name: 'Assistant',
  instructions: 'You are a concise assistant. Answer in at most three sentences.',
  model: 'openai/gpt-6.1-sol',
})
```

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { assistant } from './agents/assistant'

export const mastra = new Mastra({ agents: { assistant } })
```

```typescript
// scripts/ask.ts (run with Node 22.18+ or tsx)
import { mastra } from '../src/mastra/index.ts'

const agent = mastra.getAgentById('assistant')
const { text, usage } = await agent.generate('What is a vector database?')
console.log(text, usage)
```

`.env`: `OPENAI_API_KEY=...`

---

## 2. Agent with tools and a workflow

```typescript
import { Agent } from '@mastra/core/agent'
import { weatherTool } from '../tools/weather-tool'
import { tripPlanWorkflow } from '../workflows/trip-plan-workflow'

export const travelAgent = new Agent({
  id: 'travel-agent',
  name: 'Travel Agent',
  instructions: `
    You plan trips.
    - Use weatherTool for current conditions at a destination.
    - Use the tripPlan workflow when the user asks for a full itinerary.
    - Never invent prices. Say when you do not know.`,
  model: 'anthropic/claude-sonnet-5-5',
  tools: { weatherTool },
  workflows: { tripPlan: tripPlanWorkflow }, // exposed as tool "workflow-tripPlan"
})
```

---

## 3. Multi-tenant agent with validated request context

```typescript
import { Agent } from '@mastra/core/agent'
import { z } from 'zod'
import { searchDocsTool, adminReportTool } from '../tools'

export const tenantAgent = new Agent({
  id: 'tenant-agent',
  name: 'Tenant Agent',
  requestContextSchema: z.object({
    tenantId: z.string(),
    role: z.enum(['member', 'admin']),
  }),
  instructions: async ({ requestContext }) => {
    const tenant = await loadTenantSettings(requestContext.get('tenantId'))
    return `You support ${tenant.companyName}. Tone: ${tenant.tone}.`
  },
  model: 'openai/gpt-6.1-sol',
  tools: ({ requestContext }) =>
    requestContext.get('role') === 'admin'
      ? { searchDocsTool, adminReportTool }
      : { searchDocsTool },
})
```

```typescript
import { RequestContext } from '@mastra/core/request-context'

const requestContext = new RequestContext()
requestContext.set('tenantId', 'acme')
requestContext.set('role', 'member')

await mastra.getAgentById('tenant-agent').generate('How do I reset SSO?', {
  requestContext,
  memory: { resource: 'user-42', thread: 'acme-support-1' },
})
```

A missing `tenantId` throws `Request context validation failed for agent 'tenant-agent'` before any model call.

---

## 4. Resilient agent with model fallbacks and defaults

```typescript
import { Agent } from '@mastra/core/agent'

export const resilientAgent = new Agent({
  id: 'resilient-agent',
  name: 'Resilient Agent',
  instructions: 'You summarize documents faithfully.',
  model: [
    { model: 'openai/gpt-6.1-sol', maxRetries: 3 },
    { model: 'anthropic/claude-sonnet-5-5', maxRetries: 2 },
    { model: 'google/gemini-3.8-flash', maxRetries: 2 },
  ],
  defaultOptions: {
    maxSteps: 8,
    modelSettings: {
      temperature: 0.2,
      maxOutputTokens: 2000,
      timeout: { totalMs: 120_000, stepMs: 45_000 },
    },
  },
})
```

A `stepMs` timeout advances to the next fallback. A `totalMs` timeout ends the run.

---

## 5. Steering the loop with onIterationComplete

```typescript
const result = await agent.generate('Analyze churn drivers in this data', {
  maxSteps: 6,
  onIterationComplete: ({ iteration, text, isFinal }) => {
    if (isFinal && !text.includes('Recommendations')) {
      return { continue: true, feedback: 'Add a Recommendations section.' }
    }
    if (iteration >= 5) return { continue: false }
  },
})
```

---

## 6. Prompt caching with provider options

```typescript
export const cachedAgent = new Agent({
  id: 'cached-agent',
  name: 'Cached Agent',
  instructions: [
    { role: 'system', content: 'You are a customer service representative.' },
    {
      role: 'system',
      content: LONG_POLICY_TEXT,
      providerOptions: { anthropic: { cacheControl: { type: 'ephemeral' } } },
    },
  ],
  model: 'anthropic/claude-sonnet-5-5',
})
```

Per call: `agent.generate(msg, { providerOptions: { openai: { reasoningEffort: 'low' } } })`.
