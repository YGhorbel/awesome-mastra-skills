# Semantic recall examples

All examples follow the current docs. Model IDs come from `https://mastra.ai/models`. Verify before copying into a project on an older version.

## Contents

1. Local recall with libSQL and an explicit dimension
2. PostgreSQL with HNSW and local fastembed
3. MongoDB with server-side embeddings
4. Programmatic search with recall()

---

## 1. Local recall with libSQL and an explicit dimension

```typescript
// src/mastra/agents/support-agent.ts
import { Agent } from '@mastra/core/agent'
import { Memory } from '@mastra/memory'
import { LibSQLStore, LibSQLVector } from '@mastra/libsql'

export const supportAgent = new Agent({
  id: 'support-agent',
  name: 'SupportAgent',
  instructions: 'You are a helpful support agent.',
  model: 'openai/gpt-6.1-sol',
  memory: new Memory({
    storage: new LibSQLStore({ id: 'agent-storage', url: 'file:./local.db' }),
    vector: new LibSQLVector({ id: 'agent-vector', url: 'file:./local.db' }),
    embedder: 'openai/text-embedding-3-small',
    embeddingDimension: 1536,
    options: {
      lastMessages: 10,
      semanticRecall: {
        topK: 3,
        messageRange: 2,
        scope: 'resource',
      },
    },
  }),
})
```

```typescript
const agent = mastra.getAgentById('support-agent')

await agent.generate("Let's give them their money back.", {
  memory: { resource: 'user-123', thread: 'refund-thread' },
})

// Later, in a different thread of the same resource
const { text } = await agent.generate('What did we decide about the refund?', {
  memory: { resource: 'user-123', thread: 'followup-thread' },
})
```

`.env`: `OPENAI_API_KEY=...`

---

## 2. PostgreSQL with HNSW and local fastembed

```typescript
import { Agent } from '@mastra/core/agent'
import { Memory } from '@mastra/memory'
import { PostgresStore, PgVector } from '@mastra/pg'
import { fastembed } from '@mastra/fastembed'

export const pgAgent = new Agent({
  id: 'pg-agent',
  name: 'PG Agent',
  instructions:
    'You are an AI agent with the ability to automatically recall memories from previous interactions.',
  model: 'openai/gpt-6.1-sol',
  memory: new Memory({
    storage: new PostgresStore({
      id: 'pg-agent-storage',
      connectionString: process.env.DATABASE_URL!,
    }),
    vector: new PgVector({
      id: 'pg-agent-vector',
      connectionString: process.env.DATABASE_URL!,
    }),
    embedder: fastembed,
    options: {
      lastMessages: 10,
      semanticRecall: {
        topK: 3,
        messageRange: 2,
        indexConfig: {
          type: 'hnsw',
          hnsw: { m: 16, efConstruction: 64 },
        },
      },
    },
  }),
})
```

Install: `npm install @mastra/pg@latest @mastra/fastembed@latest`. HNSW lets recall use the index for thread and resource filters on pgvector 0.8.0 or newer.

---

## 3. MongoDB with server-side embeddings

No `embedder`: MongoDB Automated Embedding (Preview) embeds each message on write and the search text on query.

```typescript
import { Memory } from '@mastra/memory'
import { MongoDBStore, MongoDBVector } from '@mastra/mongodb'

export const memory = new Memory({
  storage: new MongoDBStore({
    id: 'agent-storage',
    uri: process.env.MONGODB_URI,
    dbName: process.env.MONGODB_DB_NAME,
  }),
  vector: new MongoDBVector({
    id: 'agent-vector',
    uri: process.env.MONGODB_URI,
    dbName: process.env.MONGODB_DB_NAME,
    autoEmbed: { model: 'voyage-4' },
  }),
  options: {
    semanticRecall: { topK: 3, messageRange: 2 },
  },
})
```

Messages saved moments ago may not be recallable yet because embedding runs in the background.

---

## 4. Programmatic search with recall()

Search one thread by meaning, for example to render "related earlier messages" in a UI. Check the caller owns the thread first.

```typescript
const agent = mastra.getAgentById('support-agent')
const memory = await agent.getMemory()

const { messages: relevant } = await memory!.recall({
  threadId: 'thread-123',
  resourceId: 'user-123',
  vectorSearchString: 'project deadline discussion',
  threadConfig: {
    semanticRecall: { topK: 5, messageRange: 1 },
  },
})

for (const m of relevant) {
  console.log(m.createdAt, m.role, m.content.parts)
}
```

Restrict recall to a project with thread metadata. Set the thread metadata on first use, and the filter on the memory config:

```typescript
import { Memory } from '@mastra/memory'

export const projectMemory = new Memory({
  // plus storage, vector, and embedder as in example 1
  options: {
    semanticRecall: {
      scope: 'resource',
      filter: { projectId: { $eq: 'project-a' } },
    },
  },
})
```

```typescript
await agent.generate('Status update please', {
  memory: {
    resource: 'user-123',
    thread: { id: 'thread-9', metadata: { projectId: 'project-a' } },
  },
})
```

The filter reads metadata captured when each message was embedded. Threads created before the metadata existed do not match.
