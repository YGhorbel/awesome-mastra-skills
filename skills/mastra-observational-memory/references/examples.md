# Observational Memory examples

All examples follow the current docs. Model IDs come from `https://mastra.ai/models`. Verify before copying into a project on an older version.

## Contents

1. Defaults with a pinned model
2. Prompt-cache-friendly tuning with a failure policy
3. Cross-thread continuity: retrieval plus resource working memory
4. Extractors, OM-managed working memory, and redaction hooks
5. Token-tiered models and custom instructions

---

## 1. Defaults with a pinned model

```typescript
// src/mastra/memory.ts
import { LibSQLStore } from '@mastra/libsql'
import { Memory } from '@mastra/memory'

export const store = new LibSQLStore({ id: 'memory-storage', url: 'file:./memory.db' })

export const memory = new Memory({
  storage: store,
  options: {
    observationalMemory: {
      model: 'openai/gpt-6-luna',
    },
  },
})
```

```typescript
// src/mastra/agents/assistant.ts
import { Agent } from '@mastra/core/agent'
import { memory } from '../memory'

export const assistant = new Agent({
  id: 'assistant',
  name: 'assistant',
  instructions: 'You are a helpful assistant.',
  model: 'openai/gpt-6-luna',
  memory,
})
```

```typescript
// scripts/session.ts
import { assistant } from '../src/mastra/agents/assistant.ts'
import { memory, store } from '../src/mastra/memory.ts'

const opts = { memory: { resource: 'user-123', thread: 'conversation-123' } }
await assistant.generate('Remember that my favorite color is blue.', opts)
const { text } = await assistant.generate('What is my favorite color?', opts)
console.log(text)

await memory.settled() // let background observation finish
await store.close()
```

---

## 2. Prompt-cache-friendly tuning with a failure policy

```typescript
import { Memory } from '@mastra/memory'

export const memory = new Memory({
  options: {
    observationalMemory: {
      model: 'auto',
      activateAfterIdle: { default: 'auto', anthropic: '1h' }, // match cacheControl.ttl by hand
      activateOnProviderChange: true,
      observation: {
        messageTokens: 30_000,
        bufferTokens: 5_000,
        bufferActivation: 0.7,
        blockAfter: 1.5,
        maxRetries: 8,
        failurePolicy: 'continue',
      },
      reflection: {
        observationTokens: 60_000,
        bufferActivation: 0.5,
        blockAfter: 1.2,
        failurePolicy: 'continue',
      },
    },
  },
})
```

`'continue'` has no backstop for a long outage: pending messages keep growing in context until the model's limit.

---

## 3. Cross-thread continuity: retrieval plus resource working memory

The replacement for deprecated `scope: 'resource'`. Each thread keeps its own observations. The agent can browse and search other threads with the `recall` tool, and small durable facts live in resource-scoped working memory.

```typescript
import { Memory } from '@mastra/memory'
import { PostgresStore, PgVector } from '@mastra/pg'

export const memory = new Memory({
  storage: new PostgresStore({ id: 'pg-storage', connectionString: process.env.DATABASE_URL }),
  vector: new PgVector({ id: 'pg-vector', connectionString: process.env.DATABASE_URL }),
  embedder: 'openai/text-embedding-3-small',
  options: {
    observationalMemory: {
      model: 'auto',
      retrieval: {
        vector: true,
        instructions: `
          Prefer the current conversation when it already contains the answer.
          For an initial scan, use a small limit with detail="low".
        `,
      },
    },
    workingMemory: {
      enabled: true,
      scope: 'resource',
    },
  },
})
```

---

## 4. Extractors, OM-managed working memory, and redaction hooks

```typescript
import { Extractor, Memory } from '@mastra/memory'
import { skillResultRedactor } from '@mastra/memory/hooks'
import { z } from 'zod'

const dropSkillResults = skillResultRedactor()

export const memory = new Memory({
  options: {
    workingMemory: { enabled: true },
    observationalMemory: {
      model: 'openai/gpt-6-luna',
      observation: {
        manageWorkingMemory: true,
        threadTitle: true,
        extract: [
          new Extractor({
            name: 'User profile',
            instructions: 'Extract stable user profile facts that should be remembered.',
            schema: z.object({
              preferredName: z.string().optional(),
              timezone: z.string().optional(),
              tools: z.array(z.string()).optional(),
            }),
          }),
          new Extractor({
            name: 'Latest blocker',
            instructions: 'Extract any blockers the agent is running into.',
            includePreviousExtraction: false,
          }),
        ],
      },
      hooks: {
        beforeObservation: async input => {
          const messages = (await dropSkillResults(input))?.messages ?? input.messages
          return { messages: messages.filter(m => m.role !== 'signal') }
        },
      },
    },
  },
})
```

Read extractor output from a stream:

```typescript
const stream = await agent.stream('Remember that I prefer dark mode.', {
  memory: { resource: 'user-1', thread: 'thread-1' },
})

for await (const chunk of stream.fullStream) {
  if (chunk.type === 'data-om-observation-end' || chunk.type === 'data-om-buffering-end') {
    const { operationType, extractedValues = {}, extractionFailures = [] } = chunk.data
    for (const [slug, value] of Object.entries(extractedValues)) {
      console.log(`${operationType} extractor ${slug}:`, value)
    }
    for (const failure of extractionFailures) {
      console.error(`Extractor ${failure.slug} failed:`, failure.error)
    }
  }
}
```

---

## 5. Token-tiered models and custom instructions

```typescript
import { Memory, ModelByInputTokens } from '@mastra/memory'

export const memory = new Memory({
  options: {
    observationalMemory: {
      observation: {
        model: new ModelByInputTokens({
          upTo: {
            40_000: 'openai/gpt-6-luna',
            1_000_000: 'google/gemini-3.8-flash',
          },
        }),
        instruction:
          'Prioritize capturing user health goals, dietary restrictions, exercise preferences, and medical considerations. Avoid capturing general chit-chat.',
        observeAttachments: 'auto',
      },
      reflection: {
        model: 'deepseek/deepseek-flash', // condenses readily
        instruction:
          'When consolidating, group related health information together. Preserve specific metrics, dates, and medical details.',
      },
    },
  },
})
```

The largest `upTo` key must cover every possible input size, or the run ends in a TripWire with empty text.
