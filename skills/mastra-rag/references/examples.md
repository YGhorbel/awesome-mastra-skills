# RAG examples

All examples follow the current docs. Check package versions before copying.

## Contents

1. Ingest and query in code
2. Agent with a vector query tool
3. Reranking retrieved results
4. Multi-tenant vector store resolver
5. Persisted GraphRAG

---

## 1. Ingest and query in code

```typescript
// src/mastra/rag/ingest.ts
import { MDocument } from '@mastra/rag'
import { ModelRouterEmbeddingModel } from '@mastra/core/llm'
import { PgVector } from '@mastra/pg'
import { embed, embedMany } from 'ai'

const embedder = new ModelRouterEmbeddingModel('openai/text-embedding-3-small')

export const pgVector = new PgVector({
  id: 'pg-vector',
  connectionString: process.env.POSTGRES_CONNECTION_STRING!,
})

export async function ingest(docId: string, markdown: string) {
  const doc = MDocument.fromMarkdown(markdown)
  const chunks = await doc.chunk({ strategy: 'recursive', maxSize: 512, overlap: 50 })

  const { embeddings } = await embedMany({
    model: embedder,
    values: chunks.map(chunk => chunk.text),
  })

  await pgVector.createIndex({ indexName: 'handbook', dimension: 1536 })

  // Remove stale chunks for this document before writing new ones
  await pgVector.deleteVectors({ indexName: 'handbook', filter: { docId } })

  await pgVector.upsert({
    indexName: 'handbook',
    vectors: embeddings,
    metadata: chunks.map(chunk => ({ text: chunk.text, docId })),
  })
}

export async function search(question: string) {
  const { embedding } = await embed({ model: embedder, value: question })
  const results = await pgVector.query({
    indexName: 'handbook',
    queryVector: embedding,
    topK: 5,
    filter: { docId: 'handbook' },
  })
  return results.map(r => ({ score: r.score, text: r.metadata?.text }))
}
```

---

## 2. Agent with a vector query tool

```typescript
// src/mastra/agents/handbook-agent.ts
import { Agent } from '@mastra/core/agent'
import { ModelRouterEmbeddingModel } from '@mastra/core/llm'
import { createVectorQueryTool } from '@mastra/rag'
import { PGVECTOR_PROMPT } from '@mastra/pg'

const vectorQueryTool = createVectorQueryTool({
  vectorStoreName: 'pgVector',
  indexName: 'handbook',
  model: new ModelRouterEmbeddingModel('openai/text-embedding-3-small'),
  description: 'Search the employee handbook for policies, benefits, and procedures',
  enableFilter: true,
})

export const handbookAgent = new Agent({
  id: 'handbook-agent',
  name: 'Handbook Agent',
  model: 'openai/gpt-6.1-sol',
  instructions: `
    You answer employee questions from the handbook.
    Always call vectorQueryTool before answering.
    Quote the relevant passage. If nothing relevant is found, say you do not know.
    ${PGVECTOR_PROMPT}`,
  tools: { vectorQueryTool },
})
```

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { handbookAgent } from './agents/handbook-agent'
import { pgVector } from './rag/ingest'

export const mastra = new Mastra({
  agents: { handbookAgent },
  vectors: { pgVector }, // matches vectorStoreName
})
```

Override retrieval per request:

```typescript
import { RequestContext } from '@mastra/core/request-context'

const requestContext = new RequestContext()
requestContext.set('topK', 3)
requestContext.set('filter', { docId: 'benefits' })

await mastra.getAgentById('handbook-agent').generate('How many vacation days do I get?', {
  requestContext,
})
```

---

## 3. Reranking retrieved results

```typescript
import { rerankWithScorer as rerank, MastraAgentRelevanceScorer } from '@mastra/rag'

const initialResults = await pgVector.query({
  indexName: 'handbook',
  queryVector: queryEmbedding,
  topK: 10,
})

const scorer = new MastraAgentRelevanceScorer('relevance-scorer', 'openai/gpt-6.1-sol')

const reranked = await rerank({
  results: initialResults,
  query: 'What is the parental leave policy?',
  scorer,
  options: {
    weights: { semantic: 0.5, vector: 0.3, position: 0.2 },
    topK: 3,
  },
})

for (const { result, score } of reranked) console.log(score, result.metadata?.text)
```

Swap the scorer for a dedicated reranker: `new CohereRelevanceScorer('rerank-v3.5')` from `@mastra/rag`, or `new VoyageRelevanceScorer({ model: 'rerank-2.5' })` from `@mastra/voyageai`.

Reranking inside the agent tool instead:

```typescript
const rerankingTool = createVectorQueryTool({
  vectorStoreName: 'pgVector',
  indexName: 'handbook',
  model: new ModelRouterEmbeddingModel('openai/text-embedding-3-small'),
  reranker: {
    model: 'openai/gpt-6.1-sol',
    options: { weights: { semantic: 0.5, vector: 0.3, position: 0.2 }, topK: 5 },
  },
})
```

---

## 4. Multi-tenant vector store resolver

```typescript
import { createVectorQueryTool, VectorStoreResolver } from '@mastra/rag'
import { ModelRouterEmbeddingModel } from '@mastra/core/llm'
import { PgVector } from '@mastra/pg'
import { RequestContext } from '@mastra/core/request-context'

const cache = new Map<string, PgVector>()

const resolveStore: VectorStoreResolver = async ({ requestContext }) => {
  const tenantId = requestContext?.get('tenantId')
  if (!tenantId) throw new Error('tenantId is required in request context')
  if (!cache.has(tenantId)) {
    cache.set(
      tenantId,
      new PgVector({
        id: `pg-vector-${tenantId}`,
        connectionString: process.env.POSTGRES_CONNECTION_STRING!,
        schemaName: `tenant_${tenantId}`,
      }),
    )
  }
  return cache.get(tenantId)!
}

export const tenantSearch = createVectorQueryTool({
  indexName: 'embeddings',
  model: new ModelRouterEmbeddingModel('openai/text-embedding-3-small'),
  vectorStore: resolveStore,
})

const requestContext = new RequestContext()
requestContext.set('tenantId', 'acme-corp')
const result = await tenantSearch.execute({ queryText: 'company policies', topK: 5 }, { requestContext })
console.log(result.sources)
```

Set `tenantId` from authenticated server middleware, never from the request body (see `mastra-server`).

---

## 5. Persisted GraphRAG

```typescript
import { readFile, writeFile } from 'node:fs/promises'
import { GraphRAG } from '@mastra/rag'
import type { GraphRAGSnapshot } from '@mastra/rag'

const SNAPSHOT_PATH = './docs-graph.json'

export async function loadOrBuildGraph(documentChunks, embeddings) {
  try {
    const snapshot = JSON.parse(await readFile(SNAPSHOT_PATH, 'utf8')) as GraphRAGSnapshot
    return GraphRAG.deserialize(snapshot)
  } catch {
    // No usable snapshot yet
  }
  const graphRag = new GraphRAG(1536, 0.7)
  graphRag.createGraph(documentChunks, embeddings)
  await writeFile(SNAPSHOT_PATH, JSON.stringify(graphRag.serialize()))
  return graphRag
}

const graph = await loadOrBuildGraph(chunks, embeddings)
const ranked = graph.query({ query: queryEmbedding, topK: 5, randomWalkSteps: 100, restartProb: 0.15 })
```

For an agent, prefer the tool form, which builds the graph from retrieved chunks on first call:

```typescript
import { createGraphRAGTool } from '@mastra/rag'

const graphQueryTool = createGraphRAGTool({
  vectorStoreName: 'pgVector',
  indexName: 'handbook',
  model: new ModelRouterEmbeddingModel('openai/text-embedding-3-small'),
  graphOptions: { dimension: 1536, threshold: 0.7 },
})
```
