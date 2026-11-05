# Semantic recall API reference

Distilled from `https://mastra.ai/docs/memory/semantic-recall.md`, `https://mastra.ai/reference/memory/memory-class.md`, `https://mastra.ai/reference/memory/recall.md`, and `https://mastra.ai/models/embeddings.md`. Verify against the installed version before relying on an option.

## Contents

- Memory constructor fields for recall
- `options.semanticRecall`
- Filter operators
- Embedder forms
- Embedding models and dimensions
- `recall()` search parameters
- Storage and vector support

---

## Memory constructor fields for recall

| Field | Type | Notes |
|---|---|---|
| `vector` | `MastraVector \| false` | Required for recall. `false` disables vector operations. |
| `embedder` | `string \| EmbeddingModel<string> \| EmbeddingModelV2<string>` | Required unless `vector.isSelfEmbedding` is true. |
| `embeddingDimension` | `number` | Positive integer. Names the index without a probe embedding. A mismatch with real output throws `MASTRA_MEMORY_EMBEDDING_DIMENSION_MISMATCH` before any index is created or queried. |
| `storage` | `MastraCompositeStore` | Messages themselves still live in storage. |

---

## `options.semanticRecall`

`boolean | { topK, messageRange, scope?, filter?, indexConfig? }`. Disabled by default. `true` uses the defaults.

| Field | Type | Default | Notes |
|---|---|---|---|
| `topK` | `number` | `4` | Similar messages to retrieve. |
| `messageRange` | `number \| { before: number; after: number }` | `{ before: 1, after: 1 }` | Context around each match. |
| `scope` | `'thread' \| 'resource'` | `'resource'` | Resource scope requires libSQL, OracleDB, PostgreSQL, MongoDB, or Upstash storage. |
| `filter` | metadata filter | none | Matches thread metadata stored on embeddings at save time. |
| `indexConfig` | object | store default | PgVector: `{ type: 'hnsw' \| 'ivfflat' \| 'flat', metric?, hnsw?: { m, efConstruction }, ivf?: { lists } }`. |

Example from the docs:

```typescript
semanticRecall: {
  topK: 5,
  messageRange: 3,
  scope: 'resource',
  indexConfig: {
    type: 'hnsw',
    metric: 'dotproduct', // recommended for OpenAI embeddings
    hnsw: { m: 16, efConstruction: 64 },
  },
}
```

Note: the semantic recall page lists HNSW defaults as `m: 16`, `efConstruction: 64`, while the PgVector page lists `m: 8`, `efConstruction: 32`. Set both values explicitly.

---

## Filter operators

`$and`, `$or`, `$eq`, `$ne`, `$gt`, `$gte`, `$lt`, `$lte`, `$in`, `$nin`.

```typescript
semanticRecall: {
  scope: 'resource',
  filter: {
    $and: [{ projectId: { $eq: 'project-a' } }, { priority: { $gte: 3 } }],
  },
}
```

Filters apply to metadata captured when each message was embedded.

---

## Embedder forms

| Form | Example | Notes |
|---|---|---|
| Router string | `embedder: 'openai/text-embedding-3-small'` | Shortest form. |
| Router model | `new ModelRouterEmbeddingModel('openai/text-embedding-3-small')` | Import from `@mastra/core/llm`. Throws at construction on unknown provider or missing key. |
| OpenRouter | `new ModelRouterEmbeddingModel({ providerId: 'openrouter', modelId: 'openai/text-embedding-3-small' })` | Uses `OPENROUTER_API_KEY`. |
| OpenAI-compatible URL | `new ModelRouterEmbeddingModel({ providerId: 'ollama', modelId: 'nomic-embed-text', url: 'http://localhost:11434/v1', apiKey: 'not-needed' })` | Local or custom endpoints. |
| FastEmbed (local) | `import { fastembed } from '@mastra/fastembed'`, `embedder: fastembed` | No API key. 512-token input window. |
| FastEmbed E5 | `embedder: fastembed.multilingualE5LargePassage` | 1024 dimensions. Use one model for both sides in memory. |
| None | MongoDB `autoEmbed: { model: 'voyage-4' }` on `MongoDBVector` | Server-side embeddings. |

Key detection: `OPENAI_API_KEY`, `GOOGLE_API_KEY` (falls back to `GOOGLE_GENERATIVE_AI_API_KEY`), `OPENROUTER_API_KEY`, `VOYAGE_API_KEY`.

---

## Embedding models and dimensions

| Model ID | Dimensions | Max tokens |
|---|---|---|
| `openai/text-embedding-3-small` | 1536 | 8191 |
| `openai/text-embedding-3-large` | 3072 | 8191 |
| `openai/text-embedding-ada-002` | 1536 | 8191 |
| `google/gemini-embedding-001` | 768 | 2048 |
| VoyageAI models (`@mastra/voyageai`) | 1024 default, 256 to 2048 configurable on most | see models page |

Type for autocomplete: `import type { EmbeddingModelId } from '@mastra/core/llm'`.

---

## `recall()` search parameters

```typescript
const memory = await agent.getMemory()
const { messages } = await memory!.recall({
  threadId: 'thread-123',
  vectorSearchString: 'What did we discuss about the project deadline?',
  threadConfig: { semanticRecall: true },
})
```

| Param | Notes |
|---|---|
| `vectorSearchString` | Text to embed and search. Requires `threadConfig.semanticRecall`. |
| `threadConfig.semanticRecall` | `boolean` or the full object above. |
| `include[].withPreviousMessages` / `withNextMessages` | Default 2 for vector search, 0 otherwise. |
| `resourceId` | Validates thread ownership. |

Returns `{ messages: MastraDBMessage[] }`.

---

## Storage and vector support

- Resource scope storage: libSQL, OracleDB, PostgreSQL, MongoDB, Upstash.
- Vector stores listed for memory: Astra, Chroma, Cloudflare Vectorize, Convex, Couchbase, DuckDB, Elasticsearch, LanceDB, libSQL, MongoDB, OpenSearch, OracleDB, Pinecone, PostgreSQL, Qdrant, S3 Vectors, Turbopuffer, Upstash. Constructor shapes in `mastra-vector-stores`.
- Only stores that embed text themselves (MongoDB Automated Embedding) run without an `embedder`.
