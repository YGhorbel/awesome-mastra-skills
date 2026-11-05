# Vector store API reference

Distilled from `https://mastra.ai/reference/rag/vector-databases.md`, `https://mastra.ai/reference/rag/metadata-filters.md`, and the `integrations/vectors/*` pages. Verify against the installed version before relying on an option.

## Contents

- Shared methods
- Query result
- Store-specific methods and options
- Filter operators by store
- Filter rules
- Index naming rules
- Registering on Mastra

---

## Shared methods

| Method | Params | Notes |
|---|---|---|
| `createIndex` | `{ indexName, dimension, metric? }` | `metric`: `'cosine'` (default on most), `'euclidean'`, `'dotproduct'`. Dimension cannot change later. |
| `upsert` | `{ indexName, vectors: number[][], metadata?: Record<string, any>[], ids?: string[] }` | Updates when IDs match. Batches automatically. |
| `query` | `{ indexName, queryVector: number[], topK?, filter?, includeVector? }` | `topK` default `10`, `includeVector` default `false`. |
| `listIndexes` | none | Index names. |
| `describeIndex` | `{ indexName }` | Dimension, count, metric (plus store extras). |
| `deleteIndex` | `{ indexName }` | |
| `updateVector` | `{ indexName, id? , filter?, update: { vector?, metadata? } }` | `id` or `filter`, not both. Filter updates not on Couchbase. |
| `deleteVector` | `{ indexName, id }` | |
| `deleteVectors` | `{ indexName, ids? , filter? }` | `ids` or `filter`, not both. Filter delete not supported on Couchbase or Vectorize. |

---

## Query result

```typescript
interface QueryResult {
  id: string
  score: number
  metadata: Record<string, any>
  vector?: number[] // only when includeVector is true
}
```

Errors are `MastraError` from `@mastra/core/error`.

---

## Store-specific methods and options

| Store | Extras |
|---|---|
| PgVector | `createIndex`: `vectorType` (`'vector' \| 'halfvec' \| 'bit' \| 'sparsevec'`), `indexConfig: { type: 'flat' \| 'hnsw' \| 'ivfflat', hnsw: { m, efConstruction }, ivf: { lists } }`, `buildIndex`, `metadataIndexes`. Metrics add `'hamming'`, `'jaccard'` for `bit`. `query`: `minScore` (default `-1`), `ef`, `probes`. Also `truncateIndex`, `buildIndex`, `disconnect`, public `pool`. |
| LibSQLVector | Cosine only. `vectorTopKOverFetchMultiplier` for filtered queries. Lock retries `maxRetries`, `initialBackoffMs`. |
| MongoDBVector | `createIndex`: `filterFields`, `autoEmbed`, `collectionName` (bring your own), `searchIndexName`, `allowWrites`. `waitForIndexReady`, `createSearchIndex`, `waitForSearchIndexReady`, `textQuery`, `hybridQuery` (MongoDB 8.0+). `query` also takes `documentFilter`, or `queryText` with `autoEmbed`. `upsert` takes `documents` with `autoEmbed`. |
| PineconeVector | Constructor `cloud`, `region`. `upsert`/`query`: `sparseVectors`/`sparseVector`, `namespace`. Use `dotproduct` for hybrid. |
| QdrantVector | `createIndex`: `namedVectors`. `upsert`: `vectorName`. `createPayloadIndex({ indexName, fieldName, fieldSchema })`, `deletePayloadIndex`. |
| ChromaVector | `upsert`: `documents`. `query`/`get`: `documentFilter`. `forkIndex`, `get`, `hybridSearch`. |
| UpstashVector | Namespaces created on upsert; `createIndex` metric ignored. Sparse vectors for hybrid. Filter update matches up to 1,000 items. |
| CloudflareVector | `createMetadataIndex` before filtering (max 10 per index). No filtered delete. |
| AzureAISearchVector | `createIndex`: `metadataIndexes`. Constructor `autoIndexMetadata`. `upsert`: `deleteFilter`. |
| S3Vectors | Constructor `nonFilterableMetadataKeys` (immutable). Index names lowercased, underscores become hyphens. Metrics cosine or euclidean. |
| TurbopufferVector | `consistency: 'strong' \| 'eventual'`, `schemaConfigForIndex`. Metrics cosine or euclidean. |
| LanceVectorStore | `LanceVectorStore.create(uri, options?)`. `createIndex`/`upsert` take `tableName`. `indexConfig.type`: `'hnsw'` (default), `'ivfflat'`, `'ivfpq'`. `createTable`. |
| OracleVector | `createIndex`: `vectorFormat`, `indexConfig: { type: 'none' \| 'ivf' \| 'hnsw', accuracy }`, `metadataIndexes`. Exact search default. |
| CouchbaseVector | Default metric `dotproduct`. No filters, no `includeVector`, delete by ID only. |
| ConvexVector | Cosine only, in-JS scoring. `ConvexNativeVector` for native search with `filterFields`. |
| DuckDBVector | Constructor `path` (`':memory:'` default), `dimensions` (1536), `metric`. HNSW via the VSS extension. |

---

## Filter operators by store

From the metadata filter reference. Couchbase supports no filters.

| Operator | Supported by |
|---|---|
| `$eq`, `$ne`, `$gt`, `$gte`, `$lt`, `$lte`, `$in`, `$nin` | All except Couchbase |
| `$and`, `$or` | All except Vectorize and Couchbase |
| `$exists` | All except Vectorize, Chroma, Couchbase |
| `$not` | Astra, Qdrant, Upstash, PgVector, libSQL, MongoDB, OracleDB |
| `$nor` | Qdrant, Upstash, PgVector, libSQL, MongoDB, OracleDB |
| `$all` | Astra, Pinecone, Qdrant, Upstash, MongoDB, OracleDB |
| `$elemMatch` | libSQL, PgVector, MongoDB, OracleDB |
| `$contains` | Upstash, libSQL, PgVector, OracleDB |
| `$regex` | Qdrant (token match), PgVector, Upstash, MongoDB, OracleDB |
| `$size` | Astra, libSQL, PgVector, MongoDB (integer only), OracleDB |
| `$geo`, `$datetime`, `$hasId`, `$hasVector` | Qdrant |

Pages that list their own sets: Azure AI Search (`$eq` to `$nin`, `$exists`, `$and`, `$or`, `$not`; others throw), S3 Vectors (`$and`, `$or`, comparisons, `$in`, `$nin`, `$exists`), Weaviate (comparisons, `$in`, `$nin`, `$all`, `$exists`, `$and`, `$or`, `$not`). Convex native: one equality field or `$or` of equalities.

---

## Filter rules

- Field names: no leading `$`, no empty names, dots only for nested fields.
- Logical operators appear at the top level or inside other logical operators, never inside a field.
- `$not` may be top level or field level.
- Values must be JSON types and not `undefined`.

---

## Index naming rules

| Store | Rule | Valid | Invalid |
|---|---|---|---|
| PgVector, libSQL | Letter or underscore start; letters, digits, `_` | `my_index_123` | `my-index` |
| MongoDB | Letter or underscore start; letters, digits, `_`, `.`; up to 120 bytes | `my_collection.123` | `my-index` |
| Astra | Letters, digits, `_`; 48 chars max | `my_collection_123` | `my-collection` |
| Pinecone | Lowercase, digits, dashes; no dots | `my-index-123` | `my.index` |
| Qdrant | 1 to 255 chars; no `< > : " / \ \| ? *` | `my_collection_123` | `my/collection` |
| Chroma | 3 to 63 chars; alphanumeric start and end; `_` and `-` allowed | `my-collection-123` | `my..collection` |
| Upstash | 2 to 100 chars; alphanumerics, `_`, `-`, `.`; no special first or last char | `MyNamespace123` | `_namespace` |
| Weaviate | Letter start; letters, digits, `_` (first letter capitalized internally) | `my_collection` | `123_collection` |
| Cloudflare | Letter start; under 32 chars; lowercase, digits, dashes | `my-index-123` | `My_Index` |
| OpenSearch, Elasticsearch | Lowercase; no leading `_` or `-`; no spaces or special chars | `my-index-123` | `My_Index` |
| S3 Vectors | 3 to 63 chars; lowercase, digits, `-`, `.` | `my-index.123` | `my_index` |
| Azure AI Search | 2 to 128 chars; lowercase, digits, `-`, `_`; no dash at ends | `my-index-123` | `MyIndex` |
| OracleDB | Logical names up to 512 chars, mapped to tables | `customer-support/docs:v1` | empty |

---

## Registering on Mastra

```typescript
import { Mastra } from '@mastra/core'
import { PineconeVector } from '@mastra/pinecone'

export const mastra = new Mastra({
  vectors: {
    pinecone: new PineconeVector({ id: 'pinecone-vector', apiKey: process.env.PINECONE_API_KEY }),
  },
})

const store = mastra.getVector('pinecone') // throws if the name is not registered
```

For memory, pass the store to `new Memory({ vector })` instead (see `mastra-semantic-recall`).
