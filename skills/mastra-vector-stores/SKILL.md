---
name: mastra-vector-stores
description: "Choose, configure, and use Mastra vector store adapters (PgVector, LibSQLVector, MongoDBVector, PineconeVector, QdrantVector, ChromaVector, and 14 more) through the shared createIndex, upsert, query, updateVector, and deleteVectors API, with dimensions, distance metrics, index tuning, and metadata filters. Use this skill whenever the user needs somewhere to store embeddings for RAG or semantic recall, compares vector databases, writes upsert or query code against a Mastra vector store, hits a dimension mismatch or index naming error, or needs a filter that a store does not support. Triggers on Mastra vector store, MastraVector, @mastra/pg PgVector, @mastra/libsql LibSQLVector, @mastra/pinecone, @mastra/qdrant, @mastra/chroma, @mastra/mongodb MongoDBVector, @mastra/s3vectors, createIndex, upsert, queryVector, topK, includeVector, metadata filter, hnsw, ivfflat, mastra.getVector. Also triggers when picking a vector DB for a Mastra project."
license: Apache-2.0
metadata:
  category: memory-and-knowledge
  catalog_summary: "Vector store adapters, common createIndex/upsert/query API, filters, index tuning, choosing a store"
  display_order: 7
  docs: https://mastra.ai/reference/rag/vector-databases
---

# Mastra Vector Stores

Pick a vector database, create an index that matches your embedder, and store and query embeddings through Mastra's shared vector API.

---

## When to use

- Choosing a vector database for a Mastra RAG pipeline or for semantic recall
- Writing `createIndex`, `upsert`, `query`, or `deleteVectors` calls
- Matching index dimension and metric to an embedding model
- Writing metadata filters and checking which operators a store supports
- Tuning PgVector HNSW or IVFFlat indexes
- Registering a shared store on `new Mastra({ vectors })`
- Fixing index naming, dimension, or filter errors

## When NOT to use

- Chunking documents and building the retrieval pipeline (use `mastra-rag`)
- Turning on recall over conversation history (use `mastra-semantic-recall`)
- Relational storage for threads, workflows, traces (use `mastra-storage`)
- Choosing an embedding model ID and its keys (use `mastra-models`)
- Knowledge graphs shared across threads (use `mastra-knowledge`)
- Exposing retrieval as an agent tool (use `mastra-rag` for `createVectorQueryTool`)

---

## Required inputs

- The embedding model and its output dimension (1536 for `openai/text-embedding-3-small`)
- Where it runs: existing database (Postgres, MongoDB, libSQL) or a managed vector service
- Expected scale (vectors, queries per second) and latency target
- Metadata fields you will filter on, and which operators you need
- Whether you need hybrid (sparse plus dense or text plus vector) search
- Tenancy model: one index per tenant, namespaces, or a tenant metadata filter

---

## The framework: one interface, many backends

Every adapter extends `MastraVector` and shares the core calls. Store-specific options sit on top.

```typescript
import { PgVector } from '@mastra/pg'
import { ModelRouterEmbeddingModel } from '@mastra/core/llm'
import { embedMany } from 'ai'

const store = new PgVector({ id: 'pg-vector', connectionString: process.env.DATABASE_URL })

await store.createIndex({ indexName: 'docs', dimension: 1536 })

const chunks = [{ text: 'Refunds are issued within 5 days.' }, { text: 'Shipping takes 2 days.' }]
const { embeddings } = await embedMany({
  model: new ModelRouterEmbeddingModel('openai/text-embedding-3-small'),
  values: chunks.map(c => c.text),
})

await store.upsert({
  indexName: 'docs',
  vectors: embeddings,
  metadata: chunks.map(c => ({ text: c.text, docId: 'faq' })),
})

const results = await store.query({
  indexName: 'docs',
  queryVector: embeddings[0],
  topK: 5,
  filter: { docId: 'faq' },
})
// [{ id, score, metadata, vector? }]
```

| Call | Purpose |
|---|---|
| `createIndex({ indexName, dimension, metric? })` | Create an index or collection. Dimension is fixed after creation |
| `upsert({ indexName, vectors, metadata?, ids? })` | Insert or update by ID. Batches automatically |
| `query({ indexName, queryVector, topK?, filter?, includeVector? })` | Similarity search. `topK` default 10 |
| `listIndexes()`, `describeIndex({ indexName })`, `deleteIndex({ indexName })` | Index management |
| `updateVector({ indexName, id \| filter, update })` | Change vector or metadata |
| `deleteVector({ indexName, id })`, `deleteVectors({ indexName, ids \| filter })` | Remove vectors |

Exceptions: Lance uses `tableName` and an async `LanceVectorStore.create(uri)`. Upstash creates namespaces on upsert. MongoDB `autoEmbed` takes `documents` and `queryText` instead of vectors.

---

## Workflow

1. **Verify the API.** If `node_modules/@mastra/` exists, read the adapter's `dist/docs/` and types. Otherwise fetch `https://mastra.ai/reference/rag/vector-databases.md` and the adapter page, for example `https://mastra.ai/integrations/vectors/pg.md`. Trust these over memory.
2. **Choose the store.** Prefer the database you already run (`PgVector`, `MongoDBVector`, `LibSQLVector`). Use `references/providers.md` for filters, metrics, and limits.
3. **Install and construct.** `npm install @mastra/<package>@latest`. Pass `id` and env-based credentials.
4. **Create the index once.** `dimension` equals the embedder output. Pick `metric` (cosine default). Follow the store's naming rules (PgVector and libSQL: no hyphens; Pinecone and Vectorize: lowercase with dashes).
5. **Declare filterable fields where required.** Qdrant `createPayloadIndex`, Vectorize `createMetadataIndex`, MongoDB `filterFields`, Azure `metadataIndexes`, S3 Vectors `nonFilterableMetadataKeys`.
6. **Upsert with metadata.** Always store the source `text` and a document ID so you can return content and delete by document.
7. **Query with filters.** Use Mastra's MongoDB-style operators. Check the store supports each one.
8. **Register for reuse.** `new Mastra({ vectors: { pgVector } })`, then `mastra.getVector('pgVector')`.
9. **Clean up stale data.** `deleteVectors({ indexName, filter: { docId } })` when a document changes.
10. **Measure.** Recall on a small labeled set, plus p95 query latency. Tune index type before scaling.

---

## Deep dive: choosing a store

| Situation | Store |
|---|---|
| Already on PostgreSQL | `PgVector` (`@mastra/pg`), HNSW index |
| Local dev or a single node | `LibSQLVector` (`@mastra/libsql`) or `DuckDBVector` (`@mastra/duckdb`) |
| MongoDB Atlas, want text plus vector or server-side embeddings | `MongoDBVector` (`hybridQuery`, `autoEmbed`) |
| Managed service, hybrid sparse plus dense | `PineconeVector` or `UpstashVector` |
| Rich filtering (geo, datetime, regex) | `QdrantVector` |
| AWS, serverless, low cost per vector | `S3Vectors` (Preview) |
| Cloudflare Workers | `CloudflareVector` (`@mastra/vectorize`) |
| Search engine already in place | `ElasticSearchVector`, `OpenSearchVector`, `AzureAISearchVector` |
| Oracle Database | `OracleVector` |
| Convex app, small data | `ConvexVector` (in-JS cosine, dev scale) |

### PgVector index tuning

```typescript
await store.createIndex({
  indexName: 'docs',
  dimension: 1536,
  metric: 'dotproduct',
  indexConfig: { type: 'hnsw', hnsw: { m: 16, efConstruction: 64 } },
  metadataIndexes: ['docId'],
})

await store.query({ indexName: 'docs', queryVector, topK: 10, ef: 100, minScore: 0.5 })
```

Default index is `ivfflat` (set `ivf.lists` near `sqrt(n) * 2`; tune `probes` at query time). HNSW gives better recall and speed but needs more memory to build. Changing `indexConfig` drops and rebuilds the index.

---

## Failure patterns

- **Dimension mismatch on upsert.** Index created for another model. Recreate the index; dimensions cannot change.
- **Invalid index name.** `my-index` fails on PgVector, libSQL, MongoDB, Astra; `my_index` fails on S3 Vectors and Pinecone. Check `references/api.md` naming rules.
- **Filter silently ignored or throwing.** Couchbase ignores filters; Vectorize throws on filtered delete; Azure throws on `$regex`, `$size`, `$all`. Check the operator table.
- **Qdrant or Vectorize filter returns nothing.** Field not indexed. Call `createPayloadIndex` or `createMetadataIndex`, then re-upsert for Vectorize.
- **MongoDB filter fails on large collections.** Undeclared filter fields take a pre-filter path limited by the 16 MB BSON size. Declare `filterFields` at index creation.
- **Results have no text.** Metadata lacked the source text. Store `text` on every upsert.
- **`includeVector: true` throws.** Not supported on Couchbase or MongoDB `autoEmbed` indexes.
- **`dotproduct` rejected.** Not supported by S3 Vectors or Turbopuffer; libSQL supports cosine only.
- **Convex vector search slow.** `ConvexVector` scores in JavaScript. Use `ConvexNativeVector` or another store beyond small datasets.
- **Pinecone metadata update wipes fields.** Updates replace the whole metadata object. Send the full object.
- **Mixed embedders in one index.** Scores become meaningless. One model per index.

---

## Output format

A finished vector store delivery contains:

- Adapter installed and constructed with `id` and env-based credentials, registered on `new Mastra({ vectors })` if shared
- Index creation code with explicit `dimension`, `metric`, and index config
- Filterable fields declared where the store requires it
- Upsert code storing `text` and a document ID in metadata
- Query code with filters limited to supported operators
- `.env.example` entries for the store and the embedder
- Evidence: a query returning expected chunks with scores

---

## Reference files

- [`references/api.md`](references/api.md) - Shared method signatures, result shape, filter operators by store, naming rules, store-specific methods.
- [`references/providers.md`](references/providers.md) - Every vector adapter: package, class, constructor, index creation, filter support.
- [`references/examples.md`](references/examples.md) - PgVector end to end, Qdrant with payload indexes, MongoDB hybrid and auto-embedding, S3 Vectors.
- [`references/checklist.md`](references/checklist.md) - Pre-production checklist for a vector store.

**Live docs**

- https://mastra.ai/reference/rag/vector-databases
- https://mastra.ai/reference/rag/metadata-filters
- https://mastra.ai/integrations/vectors/pg
- https://mastra.ai/integrations/vectors/mongodb
- https://mastra.ai/integrations/vectors/qdrant
- https://mastra.ai/reference/core/getVector
