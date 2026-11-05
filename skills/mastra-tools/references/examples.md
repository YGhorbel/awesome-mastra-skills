# Tool examples

All examples follow the current docs. Verify against the installed version before copying into a project on an older release.

## Contents

1. API tool with request context and safe side effects
2. Redacting tool with toModelOutput and transform
3. Client tool and render-only tool
4. Code mode agent with an in-process transport
5. Agent with a large tool library and tool search

---

## 1. API tool with request context and safe side effects

```typescript
// src/mastra/tools/place-order-tool.ts
import { createTool } from '@mastra/core/tools'
import { z } from 'zod'

export const placeOrderTool = createTool({
  id: 'place-order',
  description: 'Places an order and returns its id and total',
  inputSchema: z.object({ sku: z.string(), quantity: z.number().int().positive() }),
  outputSchema: z.object({ orderId: z.string(), total: z.number() }),
  // The order already exists when the result is produced. Do not let a schema
  // mismatch make the model retry it.
  outputValidation: 'warn',
  execute: async ({ sku, quantity }, { requestContext, abortSignal }) => {
    const userId = requestContext?.get('userId')
    const response = await fetch('https://orders.example.com/orders', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ userId, sku, quantity }),
      signal: abortSignal,
    })
    return await response.json()
  },
})
```

```typescript
// src/mastra/agents/shop-agent.ts
import { Agent } from '@mastra/core/agent'
import { placeOrderTool } from '../tools/place-order-tool'

export const shopAgent = new Agent({
  id: 'shop-agent',
  name: 'Shop Agent',
  instructions: `
    You help users buy products.
    Use place-order only after the user confirms the SKU and quantity.`,
  model: 'openai/gpt-6.1-sol',
  tools: { 'place-order': placeOrderTool }, // toolName matches the id
})
```

Test the tool alone against a running dev server:

```bash
npx mastra dev
npx mastra api tool execute place-order '{"sku":"ABC-1","quantity":1}'
```

---

## 2. Redacting tool with toModelOutput and transform

`toModelOutput` controls what the model sees. `transform` controls what the UI stream and transcript see. Your code still gets the raw result.

```typescript
import { createTool } from '@mastra/core/tools'
import { z } from 'zod'

export const customerTool = createTool({
  id: 'lookup-customer',
  description: 'Looks up a customer',
  inputSchema: z.object({
    customerId: z.string(),
    internalPath: z.string(),
  }),
  outputSchema: z.object({
    displayName: z.string(),
    apiKey: z.string(),
    debugScore: z.number(),
  }),
  execute: async () => {
    return {
      displayName: 'Acme',
      apiKey: 'secret-value',
      debugScore: 0.97,
    }
  },
  toModelOutput: output => ({
    type: 'content',
    value: [{ type: 'text', text: `Customer: ${output.displayName}` }],
  }),
  transform: {
    display: {
      input: ({ input }) => ({ customerId: input?.customerId }),
      output: ({ output }) => ({ displayName: output?.displayName }),
      error: () => ({ message: 'Customer lookup failed' }),
    },
    transcript: {
      input: ({ input }) => ({ customerId: input?.customerId }),
      output: ({ output }) => ({ displayName: output?.displayName }),
      error: () => ({ message: 'Customer lookup failed' }),
    },
  },
})
```

Multimodal model output:

```typescript
toModelOutput: output => ({
  type: 'content',
  value: [
    { type: 'text', text: `${output.location}: ${output.temperatureCelsius}°C and ${output.conditions}` },
    { type: 'image-url', url: output.radarImageUrl },
  ],
}),
```

---

## 3. Client tool and render-only tool

The browser runs this tool. The run ends with `finishReason: 'tool-calls'` until the client sends the result back.

```typescript
import { createTool } from '@mastra/core/tools'
import { z } from 'zod'

export const getLocationTool = createTool({
  id: 'get-location',
  description: 'Reads the user location from the browser',
  inputSchema: z.object({}),
  outputSchema: z.object({ lat: z.number(), lon: z.number() }),
  // no execute: the client runs it
  onOutput: ({ output, toolCallId }) => {
    // Client output is not validated against outputSchema. Treat it as untrusted.
    console.log(`client result for ${toolCallId}`, output)
  },
})
```

This tool only renders a card. Mastra returns `{ acknowledged: true }` and the agent keeps going in the same run.

```typescript
export const showCard = createTool({
  id: 'show-card',
  description: 'Display a product card',
  inputSchema: z.object({ productId: z.string() }),
  renderOnly: true,
})
```

Attach client tools to the supervisor, never to a subagent. For `useChat()` wiring, see `mastra-agentic-ui`.

---

## 4. Code mode agent with an in-process transport

```typescript
import { Agent } from '@mastra/core/agent'
import { createCodeMode, createTool } from '@mastra/core/tools'
import { QuickJsCodeModeTransport } from '@mastra/quickjs'
import { z } from 'zod'

const getTopProducts = createTool({
  id: 'getTopProducts',
  description: 'Get top selling products',
  inputSchema: z.object({ limit: z.number() }),
  outputSchema: z.object({
    products: z.array(z.object({ id: z.string(), name: z.string(), totalSales: z.number() })),
  }),
  execute: async ({ limit }) => fetchTopProducts(limit),
})

const getProductRatings = createTool({
  id: 'getProductRatings',
  description: 'Get ratings for a product',
  inputSchema: z.object({ productId: z.string() }),
  outputSchema: z.object({ ratings: z.array(z.object({ score: z.number() })) }),
  execute: async ({ productId }) => fetchRatings(productId),
})

const { tool, instructions } = createCodeMode(
  { tools: { getTopProducts, getProductRatings } }, // no sandbox needed
  new QuickJsCodeModeTransport({ memoryLimitMb: 128 }),
)

export const shopAnalyst = new Agent({
  id: 'shop-analyst',
  name: 'shop-analyst',
  instructions: ['You are a helpful shopping assistant.', instructions],
  model: 'openai/gpt-6.1-sol',
  tools: { execute_typescript: tool },
})
```

Asked for "the top 5 products and the average rating for each", the model emits one `execute_typescript` call that runs `external_getTopProducts`, fans out `external_getProductRatings` with `Promise.all`, and averages in JavaScript.

`fetchTopProducts` and `fetchRatings` stand in for your data layer.

---

## 5. Agent with a large tool library and tool search

```typescript
import { Agent } from '@mastra/core/agent'
import { ToolSearchProcessor, TokenLimiter } from '@mastra/core/processors'
import { githubTools } from './tools/github'
import { slackTools } from './tools/slack'
import { dbTools } from './tools/database'

const toolSearch = new ToolSearchProcessor({
  tools: { ...githubTools, ...slackTools, ...dbTools },
  search: { topK: 3, autoLoad: true },
  filter: ({ toolName, requestContext, phase }) => {
    if (phase === 'search') return true
    return requestContext?.get('plan') === 'pro' || !toolName.startsWith('premium_')
  },
})

export const opsAgent = new Agent({
  id: 'ops-agent',
  name: 'ops-agent',
  instructions: 'Search for a tool when you need a capability you do not have.',
  model: 'openai/gpt-6.1-sol',
  inputProcessors: [
    toolSearch,
    new TokenLimiter(127000), // last, so the context fits
  ],
})
```

With `autoLoad: true` the agent calls `search_tools` once and the matches are usable on the next turn. Without it, the agent calls `search_tools`, then `load_tool`.
