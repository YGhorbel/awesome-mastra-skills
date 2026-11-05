# Workflow examples

All examples follow the current docs. Model IDs come from `https://mastra.ai/models`. Verify before copying into a project on an older version.

## Contents

1. Parallel scoring, then branch routing
2. Agent pipeline with structured output
3. Batch processing with a nested workflow
4. Streaming a run with retries and lifecycle callbacks

---

## 1. Parallel scoring, then branch routing

Two checks run in parallel. `.map()` reshapes the keyed output into the shared input every branch needs.

```typescript
// src/mastra/workflows/order-routing.ts
import { createStep, createWorkflow } from '@mastra/core/workflows'
import { z } from 'zod'

const orderSchema = z.object({ amount: z.number(), inventory: z.number() })
const routingSchema = z.object({ riskScore: z.number(), inStock: z.boolean() })
const decisionSchema = z.object({ action: z.enum(['review', 'approve']) })

const scoreRisk = createStep({
  id: 'score-risk',
  inputSchema: orderSchema,
  outputSchema: z.object({ riskScore: z.number() }),
  execute: async ({ inputData }) => ({ riskScore: inputData.amount >= 1_000 ? 80 : 20 }),
})

const checkInventory = createStep({
  id: 'check-inventory',
  inputSchema: orderSchema,
  outputSchema: z.object({ inStock: z.boolean() }),
  execute: async ({ inputData }) => ({ inStock: inputData.inventory > 0 }),
})

const manualReview = createStep({
  id: 'manual-review',
  inputSchema: routingSchema,
  outputSchema: decisionSchema,
  execute: async () => ({ action: 'review' as const }),
})

const autoApprove = createStep({
  id: 'auto-approve',
  inputSchema: routingSchema,
  outputSchema: decisionSchema,
  execute: async () => ({ action: 'approve' as const }),
})

export const orderRoutingWorkflow = createWorkflow({
  id: 'order-routing',
  inputSchema: orderSchema,
  outputSchema: z.object({
    'manual-review': decisionSchema.optional(),
    'auto-approve': decisionSchema.optional(),
  }),
})
  .parallel([scoreRisk, checkInventory])
  .map(async ({ inputData }) => ({
    riskScore: inputData['score-risk'].riskScore,
    inStock: inputData['check-inventory'].inStock,
  }))
  .branch([
    [async ({ inputData }) => inputData.riskScore >= 70 || !inputData.inStock, manualReview],
    [async ({ inputData }) => inputData.riskScore < 70 && inputData.inStock, autoApprove],
  ])
  .commit()
```

The branch conditions are mutually exclusive, so exactly one key appears in the output.

---

## 2. Agent pipeline with structured output

```typescript
// src/mastra/agents/writer-agent.ts
import { Agent } from '@mastra/core/agent'

export const writerAgent = new Agent({
  id: 'writer-agent',
  name: 'Writer Agent',
  instructions: 'You write short, accurate articles.',
  model: 'openai/gpt-6.1-sol',
})
```

```typescript
// src/mastra/workflows/article-workflow.ts
import { createStep, createWorkflow } from '@mastra/core/workflows'
import { z } from 'zod'
import { writerAgent } from '../agents/writer-agent'

const articleSchema = z.object({
  title: z.string(),
  summary: z.string(),
  tags: z.array(z.string()),
})

const writeArticle = createStep(writerAgent, {
  structuredOutput: { schema: articleSchema },
})

const countTags = createStep({
  id: 'count-tags',
  inputSchema: articleSchema,
  outputSchema: z.object({ title: z.string(), tagCount: z.number() }),
  execute: async ({ inputData }) => ({ title: inputData.title, tagCount: inputData.tags.length }),
})

export const articleWorkflow = createWorkflow({
  id: 'article-workflow',
  inputSchema: z.object({ topic: z.string() }),
  outputSchema: z.object({ title: z.string(), tagCount: z.number() }),
})
  .map(async ({ inputData }) => ({ prompt: `Generate an article about: ${inputData.topic}` }))
  .then(writeArticle)
  .then(countTags)
  .commit()
```

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { writerAgent } from './agents/writer-agent'
import { articleWorkflow } from './workflows/article-workflow'

export const mastra = new Mastra({
  agents: { writerAgent },
  workflows: { articleWorkflow },
})
```

`.env`: `OPENAI_API_KEY=...`

---

## 3. Batch processing with a nested workflow

Each URL runs its own pipeline. Up to three run at once. State counts processed items.

```typescript
// src/mastra/workflows/batch-docs.ts
import { createStep, createWorkflow } from '@mastra/core/workflows'
import { z } from 'zod'

const docSchema = z.object({ url: z.string() })
const resultSchema = z.object({ url: z.string(), length: z.number() })

const download = createStep({
  id: 'download',
  inputSchema: docSchema,
  outputSchema: z.object({ url: z.string(), content: z.string() }),
  retries: 3,
  execute: async ({ inputData }) => {
    const response = await fetch(inputData.url)
    if (!response.ok) throw new Error(`Fetch failed: ${response.status}`)
    return { url: inputData.url, content: await response.text() }
  },
})

const measure = createStep({
  id: 'measure',
  inputSchema: z.object({ url: z.string(), content: z.string() }),
  outputSchema: resultSchema,
  execute: async ({ inputData }) => {
    return { url: inputData.url, length: inputData.content.length }
  },
})

const processDocument = createWorkflow({
  id: 'process-document',
  inputSchema: docSchema,
  outputSchema: resultSchema,
})
  .then(download)
  .then(measure)
  .commit()

const summarize = createStep({
  id: 'summarize',
  inputSchema: z.array(resultSchema),
  outputSchema: z.object({ totalLength: z.number(), count: z.number() }),
  execute: async ({ inputData }) => ({
    totalLength: inputData.reduce((sum, doc) => sum + doc.length, 0),
    count: inputData.length,
  }),
})

export const batchDocsWorkflow = createWorkflow({
  id: 'batch-docs',
  inputSchema: z.array(docSchema),
  outputSchema: z.object({ totalLength: z.number(), count: z.number() }),
})
  .foreach(processDocument, { concurrency: 3 })
  .then(summarize)
  .commit()
```

```typescript
const run = await mastra.getWorkflow('batchDocsWorkflow').createRun()
const result = await run.start({
  inputData: [{ url: 'https://example.com/a' }, { url: 'https://example.com/b' }],
})
if (result.status === 'success') console.log(result.result)
```

---

## 4. Streaming a run with retries and lifecycle callbacks

```typescript
// src/mastra/workflows/data-pipeline.ts
import { createStep, createWorkflow } from '@mastra/core/workflows'
import { z } from 'zod'

const load = createStep({
  id: 'load',
  inputSchema: z.object({ source: z.string() }),
  outputSchema: z.object({ recordsProcessed: z.number() }),
  execute: async ({ inputData, bail }) => {
    if (inputData.source === 'empty') return bail({ recordsProcessed: 0 })
    return { recordsProcessed: 42 }
  },
})

export const dataPipeline = createWorkflow({
  id: 'data-pipeline',
  inputSchema: z.object({ source: z.string() }),
  outputSchema: z.object({ recordsProcessed: z.number() }),
  retryConfig: { attempts: 5, delay: 2000 },
  options: {
    onFinish: async result => {
      result.logger.info('Pipeline completed', { status: result.status })
    },
    onError: async errorInfo => {
      errorInfo.logger.error('Pipeline failed', { error: errorInfo.error?.message })
    },
  },
})
  .then(load)
  .commit()
```

```typescript
const run = await mastra.getWorkflow('dataPipeline').createRun()
const stream = run.stream({ inputData: { source: 'crm' } })

for await (const chunk of stream.fullStream) {
  console.log(chunk.type)
}

const result = await stream.result
if (result.status === 'success') console.log(result.result)
else if (result.status === 'failed') {
  for (const [stepId, stepResult] of Object.entries(result.steps)) {
    if (stepResult.status === 'failed') console.error(stepId, stepResult.error)
  }
}
```
