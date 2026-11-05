# Memory examples

All examples follow the current docs. Model IDs come from `https://mastra.ai/models`. Verify before copying into a project on an older version.

## Contents

1. Chat agent with message history
2. Token-budgeted history with streamed titles
3. Schema working memory shared across threads
4. Thread management for a chat UI

---

## 1. Chat agent with message history

```typescript
// src/mastra/agents/memory-agent.ts
import { Agent } from '@mastra/core/agent'
import { Memory } from '@mastra/memory'

export const memoryAgent = new Agent({
  id: 'memory-agent',
  name: 'Memory Agent',
  instructions: 'You are a helpful assistant.',
  model: 'openai/gpt-6.1-sol',
  memory: new Memory({
    options: {
      lastMessages: 20,
    },
  }),
})
```

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { LibSQLStore } from '@mastra/libsql'
import { memoryAgent } from './agents/memory-agent'

export const mastra = new Mastra({
  agents: { memoryAgent },
  storage: new LibSQLStore({
    id: 'mastra-storage',
    url: 'file:./mastra.db',
  }),
})
```

```typescript
// scripts/chat.ts
import { mastra } from '../src/mastra/index.ts'

const agent = mastra.getAgentById('memory-agent')
const memory = { resource: 'user-123', thread: 'conversation-123' }

await agent.generate('Remember my favorite color is blue.', { memory })
const { text } = await agent.generate("What's my favorite color?", { memory })
console.log(text) // "Your favorite color is blue."
```

`.env`: `OPENAI_API_KEY=...`

---

## 2. Token-budgeted history with streamed titles

Use a token budget when tool results vary in size. Stream the generated title so the UI can rename the thread without polling.

```typescript
import { Agent } from '@mastra/core/agent'
import { Memory } from '@mastra/memory'

export const supportAgent = new Agent({
  id: 'support-agent',
  name: 'Support agent',
  instructions: 'Answer customer support questions.',
  model: 'openai/gpt-6.1-sol',
  memory: new Memory({
    options: {
      messageHistory: { maxTokens: 8_000, atMaxRemoveTokens: 2_000 },
      generateTitle: {
        model: 'openai/gpt-6-luna',
        instructions: 'Generate a short title.',
        emitEvent: true,
      },
    },
  }),
})
```

```typescript
const stream = await supportAgent.stream('My invoice is wrong', {
  memory: { resource: 'user-456', thread: 'thread-123' },
})

for await (const chunk of stream.fullStream) {
  if (chunk.type === 'data-thread-title') {
    renameThreadInSidebar(chunk.data.threadId, chunk.data.title)
  }
}
```

`emitEvent` delays `finish` on the turn that generates the title. `generate()` cannot carry the chunk; the title is still saved.

---

## 3. Schema working memory shared across threads

```typescript
import { Agent } from '@mastra/core/agent'
import { Memory } from '@mastra/memory'
import { z } from 'zod'

const userProfileSchema = z.object({
  name: z.string().optional(),
  location: z.string().optional(),
  timezone: z.string().optional(),
  preferences: z
    .object({
      communicationStyle: z.string().optional(),
      projectGoal: z.string().optional(),
      deadlines: z.array(z.string()).optional(),
    })
    .optional(),
})

export const assistant = new Agent({
  id: 'personal-assistant',
  name: 'PersonalAssistant',
  instructions: `You are a helpful personal assistant.
Update working memory whenever the user shares their name, location, timezone, or preferences.`,
  model: 'openai/gpt-6.1-sol',
  memory: new Memory({
    options: {
      workingMemory: {
        enabled: true,
        scope: 'resource',
        schema: userProfileSchema,
      },
    },
  }),
})
```

```typescript
// Thread A
await assistant.generate("I'm Sam from Berlin, usually on CET.", {
  memory: { thread: 'thread-a', resource: 'user-alice-456' },
})

// Thread B, same resource: the profile is already in context
await assistant.generate('What timezone am I in?', {
  memory: { thread: 'thread-b', resource: 'user-alice-456' },
})

// Merge a field from your own code (schema + resource scope + @mastra/pg only)
const memory = await assistant.getMemory()
if (memory && (await memory.supportsAtomicWorkingMemoryMerge())) {
  await memory.mergeWorkingMemory({
    threadId: 'thread-b',
    resourceId: 'user-alice-456',
    workingMemory: { preferences: { communicationStyle: 'formal' } },
  })
}
```

---

## 4. Thread management for a chat UI

Memory does not enforce access control. Check that the signed-in user owns `resourceId` before each call.

```typescript
import { mastra } from '../src/mastra/index.ts'

const agent = mastra.getAgentById('support-agent')
const memory = await agent.getMemory()

// Sidebar: newest threads first, 10 per page
const { threads, hasMore } = await memory!.listThreads({
  filter: { resourceId: 'user-123', metadata: { status: 'active' } },
  orderBy: { field: 'updatedAt', direction: 'DESC' },
  page: 0,
  perPage: 10,
})

// Open a thread
const thread = await memory!.getThreadById({ threadId: threads[0].id })
const { messages } = await memory!.recall({
  threadId: thread!.id,
  resourceId: 'user-123', // validates ownership
  perPage: 50,
  page: 0,
})

// Branch a conversation before a risky edit
const { thread: branch } = await memory!.cloneThread({
  sourceThreadId: thread!.id,
  title: 'Alternative approach',
  options: { messageLimit: 20 },
})
await agent.generate('Try a different approach', {
  memory: { thread: branch.id, resource: branch.resourceId },
})

// Delete specific messages
await memory!.deleteMessages(messages.slice(0, 2).map(m => m.id))
```

Convert `MastraDBMessage[]` for AI SDK UIs:

```typescript
import { toAISdkV5Messages } from '@mastra/ai-sdk/ui'

const uiMessages = toAISdkV5Messages(messages)
```
