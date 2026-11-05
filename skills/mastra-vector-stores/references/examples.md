# Vector store examples

All examples follow the current docs. Verify before copying into a project on an older version.

## Contents

1. PgVector end to end, registered on Mastra
2. Qdrant with payload indexes
3. MongoDB: declared filter fields, hybrid search, and Automated Embedding
4. S3 Vectors with non-filterable text

---

## 1. PgVector end to end, registered on Mastra

```typescript
// src/mastra/index.ts
import { Mastra } from '@mastra/core'
import { PgVector } from '@mastra/pg'

export const mastra = new Mastra({
  vectors: {
    pgVector: new PgVector({
      id: 'pg-vector',
      connectionString: process.env.DATABASE_URL,
    }),
  },
})
```

```typescript
// scripts/index-docs.ts
import { ModelRouterEmbeddingModel } from '@mastra/core/llm'
import { embedMany } from 'ai'
import { mastra } from '../src/mastra/index.ts'

const store = mastra.getVector('pgVector')
const embedder = new ModelRouterEmbeddingModel('openai/text-embedding-3-small')

await store.createIndex({
  indexName: 'docs',
  dimension: 1536,
  indexConfig: { type: 'hnsw', hnsw: { m: 16, efConstruction: 64 } },
  metadataIndexes: ['docId'],
})

const chunks = [
  { text: 'Refunds are issued within 5 business days.', docId: 'refund-policy' },
  { text: 'Standard shipping takes 2 to 4 days.', docId: 'shipping-policy' },
]

const { embeddings } = await embedMany({ model: embedder, values: chunks.map(c => c.text) })

// Re-indexing a document: remove its old chunks first
await store.deleteVectors({ indexName: 'docs', filter: { docId: { $in: ['refund-policy', 'shipping-policy'] } } })

await store.upsert({
  indexName: 'docs',
  vectors: embeddings,
  metadata: chunks.map(c => ({ text: c.text, docId: c.docId, createdAt: new Date().toISOString() })),
})

const { embeddings: [queryVector] } = await embedMany({ model: embedder, values: ['How long do refunds take?'] })

const results = await store.query({
  indexName: 'docs',
  queryVector,
  topK: 3,
  filter: { docId: { $eq: 'refund-policy' } },
  minScore: 0.3,
})

for (const r of results) console.log(r.score.toFixed(3), r.metadata.text)
```

`.env`: `DATABASE_URL=...`, `OPENAI_API_KEY=...`

---

## 2. Qdrant with payload indexes

Qdrant filters only on indexed payload fields.

```typescript
import { QdrantVector } from '@mastra/qdrant'

const store = new QdrantVector({
  id: 'qdrant-vector',
  url: process.env.QDRANT_URL,
  apiKey: process.env.QDRANT_API_KEY,
})

await store.createIndex({ indexName: 'my_index', dimension: 1536 })

await store.createPayloadIndex({
  indexName: 'my_index',
  fieldName: 'source',
  fieldSchema: 'keyword',
})

await store.upsert({
  indexName: 'my_index',
  vectors: embeddings,
  metadata: chunks.map(chunk => ({ text: chunk.text, source: chunk.source })),
})

const results = await store.query({
  indexName: 'my_index',
  queryVector,
  filter: { source: 'document-a' },
})
```

`$regex` on Qdrant matches whole tokens, not substrings.

---

## 3. MongoDB: declared filter fields, hybrid search, and Automated Embedding

```typescript
import { MongoDBVector } from '@mastra/mongodb'

const store = new MongoDBVector({
  id: 'mongodb-vector',
  uri: process.env.MONGODB_URI,
  dbName: process.env.MONGODB_DB_NAME,
})

// Client-side embeddings with declared filter fields
await store.createIndex({
  indexName: 'my_index',
  dimension: 1536,
  filterFields: ['category', 'price'],
})

await store.upsert({
  indexName: 'my_index',
  vectors: embeddings,
  metadata: chunks.map(chunk => ({ text: chunk.text, category: chunk.category, price: chunk.price })),
})

// Hybrid vector plus BM25 (MongoDB 8.0+)
await store.createSearchIndex({ indexName: 'my_index', fields: ['text'] })
const hybrid = await store.hybridQuery({
  indexName: 'my_index',
  queryVector,
  query: 'search terms',
  paths: ['text'],
  topK: 10,
})
```

Automated Embedding (Preview): MongoDB embeds text on write and query.

```typescript
await store.createIndex({
  indexName: 'movies',
  autoEmbed: { model: 'voyage-4' },
  filterFields: ['year'],
})

await store.waitForIndexReady({ indexName: 'movies', timeoutMs: 300000 })

await store.upsert({
  indexName: 'movies',
  documents: [
    'A lonely astronaut adrift near a strange ocean planet.',
    'A heist crew robs a bank vault in Paris.',
  ],
  metadata: [{ year: 1972 }, { year: 2001 }],
})

const results = await store.query({
  indexName: 'movies',
  queryText: 'space opera about isolation',
  topK: 5,
  filter: { year: { $gt: 1970 } },
})
```

`includeVector: true` throws on an `autoEmbed` index. The Voyage key must be provisioned through the Atlas UI.

---

## 4. S3 Vectors with non-filterable text

```typescript
import { S3Vectors } from '@mastra/s3vectors'

const store = new S3Vectors({
  id: 's3-vectors',
  vectorBucketName: 'my-vector-bucket',
  clientConfig: { region: 'us-east-1' },
  nonFilterableMetadataKeys: ['content'], // large text stored but not filterable
})

await store.createIndex({ indexName: 'my-index', dimension: 1536 })

await store.upsert({
  indexName: 'my-index',
  vectors: embeddings,
  metadata: chunks.map(chunk => ({ content: chunk.text, genre: chunk.genre, year: chunk.year })),
})

const results = await store.query({
  indexName: 'my-index',
  queryVector,
  topK: 10,
  filter: { genre: { $in: ['documentary', 'comedy'] }, year: { $gte: 2020 } },
})
```

S3 Vectors is a Preview service. Use `cosine` or `euclidean`; `dotproduct` is not supported. Index names are lowercased and underscores become hyphens.
