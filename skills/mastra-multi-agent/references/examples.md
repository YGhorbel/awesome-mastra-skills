# Multi-agent examples

All examples follow the current docs. Model IDs come from the docs pages they were taken from. Verify before copying into a project on an older version.

## Contents

1. Research and writing supervisor with memory
2. Guarded delegation: prompt rewrites, filtering, tenant metadata
3. Rubric self-correction loop
4. Council pattern with workflow parallelism

---

## 1. Research and writing supervisor with memory

```typescript
// src/mastra/agents/research-supervisor.ts
import { Agent } from '@mastra/core/agent'
import { Memory } from '@mastra/memory'
import { LibSQLStore } from '@mastra/libsql'

export const researchAgent = new Agent({
  id: 'research-agent',
  name: 'Research Agent',
  description: `Specializes in gathering factual information and data on any topic.
    Returns concise bullet-point summaries with key facts and sources.
    Does not write full articles or narrative content.`,
  instructions: 'Research the requested topic. Return bullet points with sources.',
  model: 'openai/gpt-6-luna',
  defaultOptions: { maxSteps: 5 },
})

export const writingAgent = new Agent({
  id: 'writing-agent',
  name: 'Writing Agent',
  description: `Transforms research material into well-structured written content.
    Produces full paragraphs and complete articles.
    Best used after research has been gathered.`,
  instructions: 'Write a clear, well-structured article from the provided research.',
  model: 'openai/gpt-6-luna',
})

export const supervisorAgent = new Agent({
  id: 'supervisor-agent',
  name: 'Supervisor Agent',
  instructions: `You coordinate research and writing tasks using specialized agents.

Available resources:
- researchAgent: Gathers factual data and sources (returns bullet points)
- writingAgent: Transforms research into narrative content (returns full paragraphs)

Delegation strategy:
1. For research requests: Delegate to researchAgent first
2. For writing requests: Delegate to writingAgent (provide research if available)
3. For complex requests: Delegate to researchAgent first, then writingAgent

Success criteria:
- All user questions are fully answered
- Response is well-formatted and complete
- If information is incomplete, continue iterating`,
  model: 'openai/gpt-6.1-sol',
  agents: { researchAgent, writingAgent },
  memory: new Memory({
    storage: new LibSQLStore({ id: 'storage', url: 'file:mastra.db' }),
  }),
})
```

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { supervisorAgent, researchAgent, writingAgent } from './agents/research-supervisor'

export const mastra = new Mastra({ agents: { supervisorAgent, researchAgent, writingAgent } })
```

```typescript
const supervisor = mastra.getAgentById('supervisor-agent')

const stream = await supervisor.stream('Research AI in education and write an article', {
  maxSteps: 10,
  memory: { resource: 'user-123', thread: 'articles' },
})

for await (const chunk of stream.textStream) process.stdout.write(chunk)
```

`.env`: `OPENAI_API_KEY=...`

---

## 2. Guarded delegation: prompt rewrites, filtering, tenant metadata

Put shared hooks in `defaultOptions` so every call gets them. Per-call `delegation` options work the same way.

```typescript
import { Agent } from '@mastra/core/agent'
import { Memory } from '@mastra/memory'
import { researchAgent, writingAgent } from './research-supervisor'

export const guardedSupervisor = new Agent({
  id: 'guarded-supervisor',
  name: 'Guarded Supervisor',
  instructions: 'Coordinate research and writing using the available agents.',
  model: 'openai/gpt-6.1-sol',
  agents: { researchAgent, writingAgent },
  memory: new Memory(),
  defaultOptions: {
    maxSteps: 10,
    delegation: {
      hookErrorStrategy: 'throw',
      onDelegationStart: async context => {
        // Pass a value down to the subagent's tools and dynamic config
        context.requestContext.set('audience', 'technical')

        if (context.primitiveId === 'research-agent') {
          return {
            proceed: true,
            modifiedPrompt: `${context.prompt}\n\nFocus on 2024-2025 data.`,
            modifiedMaxSteps: 5,
          }
        }
        if (context.iteration > 8) {
          return {
            proceed: false,
            rejectionReason: 'Max iterations reached. Synthesize current findings.',
          }
        }
        return { proceed: true }
      },
      messageFilter: ({ messages }) =>
        messages
          .filter(msg => {
            const content = typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content)
            return !content.includes('confidential')
          })
          .slice(-10),
      onDelegationComplete: async context => {
        if (context.error) {
          context.bail()
          return {
            feedback: `Delegation to ${context.primitiveId} failed. Try a different approach.`,
          }
        }
      },
    },
  },
})
```

Detect hook failures after the run:

```typescript
import { RequestContext } from '@mastra/core/request-context'

const requestContext = new RequestContext()
await guardedSupervisor.generate('Research AI trends', { maxSteps: 10, requestContext })
const hookErrors = requestContext.get('__mastra_delegationHookErrors') ?? []
```

---

## 3. Rubric self-correction loop

The grader checks the output after each iteration. Failed criteria come back as feedback and the supervisor tries again until all required criteria pass or `maxSteps` runs out.

```typescript
import { Agent } from '@mastra/core/agent'
import { createRubricScorer } from '@mastra/evals/scorers/prebuilt'
import { researchAgent, writingAgent } from './research-supervisor'

const parentAgent = new Agent({
  id: 'parent-agent',
  name: 'Parent Agent',
  instructions: 'You coordinate research and writing using specialized agents.',
  model: 'openai/gpt-6.1-sol',
  agents: { researchAgent, writingAgent },
})

const rubricScorer = createRubricScorer({
  model: 'openai/gpt-6-luna',
  criteria: [
    { description: 'Includes an analysis section', required: true },
    { description: 'Includes concrete recommendations', required: true },
    { description: 'Includes citations', required: false },
  ],
})

const stream = await parentAgent.stream('Research AI in education', {
  maxSteps: 10,
  isTaskComplete: {
    scorers: [rubricScorer],
    strategy: 'all',
    onComplete: async result => {
      console.log('Task complete:', result.complete)
    },
  },
  onIterationComplete: async context => {
    console.log(`Iteration ${context.iteration}/${context.maxIterations}: ${context.finishReason}`)
    return { continue: true }
  },
})

for await (const chunk of stream.textStream) process.stdout.write(chunk)
```

A custom binary scorer works the same way:

```typescript
import { createScorer } from '@mastra/core/evals'

const taskCompleteScorer = createScorer({
  id: 'task-complete',
  name: 'Task Completeness',
}).generateScore(async context => {
  const text = (context.run.output || '').toString()
  return text.includes('analysis') && text.includes('recommendation') ? 1 : 0
})
```

---

## 4. Council pattern with workflow parallelism

Mastra has no council primitive. Run independent agents in `.parallel()` and synthesize in a final step. Each parallel output is keyed by step `id`.

```typescript
import { createWorkflow, createStep } from '@mastra/core/workflows'
import { z } from 'zod'

const optimist = createStep({
  id: 'optimist',
  inputSchema: z.object({ question: z.string() }),
  outputSchema: z.object({ answer: z.string() }),
  execute: async ({ inputData, mastra }) => {
    const agent = mastra.getAgentById('optimist-agent')
    const { text } = await agent.generate(inputData.question)
    return { answer: text }
  },
})

const skeptic = createStep({
  id: 'skeptic',
  inputSchema: z.object({ question: z.string() }),
  outputSchema: z.object({ answer: z.string() }),
  execute: async ({ inputData, mastra }) => {
    const agent = mastra.getAgentById('skeptic-agent')
    const { text } = await agent.generate(inputData.question)
    return { answer: text }
  },
})

const synthesize = createStep({
  id: 'synthesize',
  inputSchema: z.object({
    optimist: z.object({ answer: z.string() }),
    skeptic: z.object({ answer: z.string() }),
  }),
  outputSchema: z.object({ verdict: z.string() }),
  execute: async ({ inputData, mastra }) => {
    const judge = mastra.getAgentById('judge-agent')
    const { text } = await judge.generate(
      `Compare these answers and give one verdict.\nA: ${inputData.optimist.answer}\nB: ${inputData.skeptic.answer}`,
    )
    return { verdict: text }
  },
})

export const councilWorkflow = createWorkflow({
  id: 'council',
  inputSchema: z.object({ question: z.string() }),
  outputSchema: z.object({ verdict: z.string() }),
})
  .parallel([optimist, skeptic])
  .then(synthesize)
  .commit()
```

Register the three agents and the workflow on `new Mastra({ agents, workflows })`. See `mastra-workflows` for running and streaming the workflow.
